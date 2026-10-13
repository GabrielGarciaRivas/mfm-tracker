"""Entry point of the packaged "Free Market Tracker" app.

Double-click: opens the live window. With arguments it behaves like the mfm-tracker command
("Free Market Tracker" deals, ... item NAME, ...).
"""
import sys
import traceback


def _log_path():
    import mfm
    return mfm.DATA / "app.log"


def main():
    # A windowed app has no console: keep print() output in a log file instead
    if sys.stdout is None or sys.stderr is None:
        try:
            log = open(_log_path(), "a", encoding="utf-8", buffering=1)
            sys.stdout = sys.stdout or log
            sys.stderr = sys.stderr or log
        except OSError:
            import io
            sys.stdout = sys.stdout or io.StringIO()
            sys.stderr = sys.stderr or io.StringIO()
    try:
        if len(sys.argv) > 1:
            import mfm
            mfm.main()
        else:
            import mfm_gui
            mfm_gui.main()
    except SystemExit:
        raise
    except Exception:
        text = traceback.format_exc()
        try:
            with open(_log_path(), "a", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Free Market Tracker", "Something went wrong:\n\n"
                                 + text[-1500:] + f"\n\nDetails were saved to {_log_path()}")
        except Exception:
            print(text, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
