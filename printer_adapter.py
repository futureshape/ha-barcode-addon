import asyncio
import os

try:
    from qutie_printer import Alignment, Concentration, QutiePrinter
except ImportError:  # pragma: no cover - exercised in environments without the library
    Alignment = None
    Concentration = None
    QutiePrinter = None


def resolve_printer_address():
    return (
        os.getenv("PRINTER_ADDRESS")
        or os.getenv("QUTIE_PRINTER_ADDRESS")
        or "AA:BB:CC:DD:EE:FF"
    )


def _align_for(value):
    if Alignment is None:
        return None
    mapping = {
        "left": Alignment.LEFT,
        "center": Alignment.CENTER,
        "right": Alignment.RIGHT,
    }
    return mapping.get((value or "center").lower(), Alignment.CENTER)


def _concentration_for(value):
    if Concentration is None:
        return None
    mapping = {
        1: Concentration.LIGHT,
        2: Concentration.MEDIUM_LOW,
        3: Concentration.MEDIUM_HIGH,
        4: Concentration.DARK,
    }
    return mapping.get(value, Concentration.MEDIUM_HIGH)


def print_with_qutie_printer(image_path, printer_address=None, darkness=3, align="center", force=False):
    if printer_address is None:
        printer_address = resolve_printer_address()

    if QutiePrinter is None:
        raise RuntimeError(
            "qutie-printer is not installed. Install it with: "
            "pip install git+https://github.com/futureshape/qutie-printer.git"
        )

    async def _run():
        printer = QutiePrinter(printer_address, verbose=True)
        try:
            await printer.connect()
            status = await printer.get_status()
            if status and not status.is_ready:
                if not force:
                    raise RuntimeError(f"Printer reports not ready: {status}")

            await printer.print_image(
                image_path,
                concentration=_concentration_for(darkness),
                alignment=_align_for(align),
                feed_after=True,
                dither=True,
            )
        finally:
            await printer.disconnect()

    asyncio.run(_run())
