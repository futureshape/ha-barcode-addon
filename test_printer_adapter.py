import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class PrinterAdapterTests(unittest.TestCase):
    def test_resolve_printer_address_prefers_env(self):
        with patch.dict(os.environ, {"PRINTER_ADDRESS": "AA:BB:CC:DD:EE:FF"}, clear=True):
            from printer_adapter import resolve_printer_address

            self.assertEqual(resolve_printer_address(), "AA:BB:CC:DD:EE:FF")

    def test_print_with_qutie_printer_calls_qutie_api(self):
        with patch.dict(os.environ, {"PRINTER_ADDRESS": "AA:BB:CC:DD:EE:FF"}, clear=True):
            from printer_adapter import print_with_qutie_printer

            mock_printer = MagicMock()
            mock_printer.connect = AsyncMock()
            mock_printer.get_status = AsyncMock(return_value=MagicMock(is_ready=True))
            mock_printer.print_image = AsyncMock()
            mock_printer.disconnect = AsyncMock()

            with patch("printer_adapter.QutiePrinter", return_value=mock_printer):
                print_with_qutie_printer("/tmp/label.png")

            mock_printer.connect.assert_awaited_once()
            mock_printer.get_status.assert_awaited_once()
            mock_printer.print_image.assert_awaited_once()
            self.assertEqual(mock_printer.print_image.await_args.args[0], "/tmp/label.png")
            self.assertEqual(mock_printer.print_image.await_args.kwargs["dither"], True)
            self.assertEqual(mock_printer.print_image.await_args.kwargs["feed_after"], True)
            mock_printer.disconnect.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
