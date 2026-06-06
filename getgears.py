import asyncio
import csv
import time
from itertools import cycle

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

console = Console()

TAXONOMY = "gUtxkR951g3VPgRkb5ay8u"
BASE_URL = "https://catalog.roblox.com/v2/search/items/details"
CATALOG_APPEND = f"?taxonomy={TAXONOMY}&creatorName=Roblox&creatorType=User&salesTypeFilter=1&includeNotForSale=true&limit=120"
MAX_RETRIES = 3
RETRY_DELAY = 30
CONCURRENT_REQUESTS = 3  # tune to taste
USE_PROXY = False

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Host": "catalog.roblox.com",
    "Priority": "u=0, i",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
    "TE": "trailers",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
}


async def fetch_proxies() -> list[str]:
    async with httpx.AsyncClient() as client:
        with console.status("[bold cyan]Fetching Mullvad proxies..."):
            resp = await client.get("https://api.mullvad.net/www/relays/wireguard/")

    raw: list[str] = []
    try:
        data = resp.json()
        if not isinstance(data, list):
            console.print(f"[yellow]Unexpected proxy response:[/yellow] {data}")
            return raw
        for relay in data:
            if isinstance(relay, dict) and relay.get("active"):
                fqdn = relay.get("fqdn")
                port = relay.get("socks_port")
                if fqdn and port:
                    raw.append(f"socks5://{fqdn}:{port}")
    except ValueError as e:
        console.print(f"[red]Failed to parse proxy JSON:[/red] {e}")

    console.print(f"[green]Loaded {len(raw)} proxies[/green]")
    return raw


async def fetch_page(
    url: str,
    proxy_cycle: cycle | None,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    headers = HEADERS
    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                proxy = next(proxy_cycle) if proxy_cycle else None
                async with httpx.AsyncClient(
                    proxy=proxy, timeout=30, headers=headers
                ) as client:
                    resp = await client.get(url)
            except httpx.ProxyError as e:
                console.print(f"[yellow]Proxy error ({proxy}): {e} — rotating[/yellow]")
                continue
            except httpx.RequestError as e:
                console.print(f"[yellow]Request error: {e} — retrying[/yellow]")
                await asyncio.sleep(2)
                continue

            if resp.status_code == 429:
                console.print(
                    f"[yellow]❗ 429 received. Waiting {RETRY_DELAY}s "
                    f"(attempt {attempt}/{MAX_RETRIES})...[/yellow]"
                )
                await asyncio.sleep(RETRY_DELAY)
                continue

            if resp.status_code != 200:
                console.print(f"[red]❗ Status {resp.status_code} for {url}[/red]")
                return None

            return resp.json()

        console.print(f"[bold red]❗ Exhausted retries for {url}[/bold red]")
        return None


async def collect_cursors() -> list[str | None]:
    """
    First pass: paginate just enough to collect all cursors,
    then we can fetch all pages concurrently.
    """
    cursors: list[str | None] = [None]  # None = first page (no cursor)
    url = BASE_URL + CATALOG_APPEND

    # Lightweight client just for cursor discovery (no proxy needed)
    async with httpx.AsyncClient(timeout=30) as client:
        with console.status("[cyan]Collecting page cursors..."):
            while True:
                page_url = url if cursors[-1] is None else f"{url}&cursor={cursors[-1]}"
                try:
                    resp = await client.get(page_url)
                    data = resp.json()
                except Exception as e:
                    console.print(f"[red]Cursor discovery failed: {e}[/red]")
                    break

                cursor = data.get("nextPageCursor")
                if not cursor or not data.get("data"):
                    break
                cursors.append(cursor)

    console.print(f"[green]Found {len(cursors)} page(s) to fetch[/green]")
    return cursors


def page_url(cursor: str | None) -> str:
    base = BASE_URL + CATALOG_APPEND
    return base if cursor is None else f"{base}&cursor={cursor}"


async def get_roblox_made_gear(proxy_cycle: cycle | None) -> list[dict]:
    cursors = await collect_cursors()
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    completed = 0
    collected = 0

    async def fetch_one(cursor: str | None, index: int) -> list[dict]:
        nonlocal completed, collected
        await asyncio.sleep(index * 0.5)  # stagger: 0s, 0.5s, 1s, ...
        data = await fetch_page(page_url(cursor), proxy_cycle, semaphore)
        completed += 1
        if data:
            items = data.get("data", [])
            collected += len(items)
            progress.update(
                task,
                advance=1,
                description=(
                    f"[cyan]Fetching pages "
                    f"[white]{completed}[/white]/[white]{len(cursors)}[/white]... "
                    f"[green]{collected} items collected[/green]"
                ),
            )
            return items
        progress.update(task, advance=1)
        return []

    with Progress(
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[cyan]Fetching {len(cursors)} page(s)...",
            total=len(cursors),
        )
        results = await asyncio.gather(
            *[fetch_one(c, i) for i, c in enumerate(cursors)]
        )

    gear_items: list[dict] = []
    for page_items in results:
        gear_items.extend(page_items)

    seen: set[int] = set()
    unique: list[dict] = []
    for item in gear_items:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique.append(item)

    return unique


async def main() -> None:
    if USE_PROXY:
        raw_proxies = await fetch_proxies()
        if not raw_proxies:
            console.print("[bold red]No proxies available — aborting.[/bold red]")
            return
        proxy_cycle = cycle(raw_proxies)
    else:
        console.print("[dim]Proxies disabled — using direct connection[/dim]")
        proxy_cycle = None

    gear_items = await get_roblox_made_gear(proxy_cycle)

    rows: list[list[str]] = [["id", "name"]]
    lines: list[str] = []

    for gear in gear_items:
        rows.append([gear["id"], gear["name"]])
        lines.append(f"ID: {gear['id']}, Name: {gear['name']}")

    with open("data.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    with open("data.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    console.print("")
    console.print(
        f"[bold green]Total gears scraped:[/bold green] [cyan]{len(gear_items)}[/cyan]"
    )


if __name__ == "__main__":
    asyncio.run(main())
