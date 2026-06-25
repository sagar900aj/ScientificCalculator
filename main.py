from __future__ import annotations

import ast
import math
import operator
import tkinter as tk
from typing import Any


class SafeEval(ast.NodeVisitor):
    """Evaluate a restricted set of AST nodes to avoid unsafe eval()."""

    ALLOWED_FUNCS = {
        "sin": lambda x: math.sin(math.radians(x)),
        "cos": lambda x: math.cos(math.radians(x)),
        "tan": lambda x: math.tan(math.radians(x)),
        "sqrt": math.sqrt,
        "sqr": lambda x: x * x,
        "pow": math.pow,
        "log10": math.log10,
        "ln": math.log,
        "log": math.log10,
    }

    CONSTANTS = {"pi": math.pi, "e": math.e}

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
    }

    def visit(self, node: ast.AST) -> Any:
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, None)
        if visitor is None:
            raise ValueError(f"Unsupported expression: {node.__class__.__name__}")
        return visitor(node)

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type in self.OPERATORS:
            return self.OPERATORS[op_type](left, right)
        raise ValueError("Unsupported binary operator")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError("Unsupported unary operator")

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed")
        fname = node.func.id
        if fname not in self.ALLOWED_FUNCS:
            raise ValueError(f"Function {fname} not allowed")
        args = [self.visit(a) for a in node.args]
        return self.ALLOWED_FUNCS[fname](*args)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.CONSTANTS:
            return self.CONSTANTS[node.id]
        raise ValueError(f"Unknown identifier: {node.id}")

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only int/float constants allowed")

    # Compatibility for older AST nodes (Python <3.8)
    def visit_Num(self, node: ast.Num) -> Any:  # type: ignore
        return node.n


def safe_eval(expr: str) -> float:
    """Safely evaluate the user expression string and return a numeric result.

    Supported additions: '^' -> power, percent handled by inserting '/100'.
    Trig functions use degrees (user friendly for beginners).
    """
    if not expr:
        raise ValueError("Empty expression")

    # Basic sanitization and token replacements
    expr = expr.replace("^", "**")
    expr = expr.replace("×", "*")
    expr = expr.replace("÷", "/")
    expr = expr.replace("%", "/100")
    expr = expr.replace("√", "sqrt")

    # Parse and evaluate safely
    node = ast.parse(expr, mode="eval")
    evaluator = SafeEval()
    return evaluator.visit(node)


class CalculatorApp:
    MAX_DISPLAY = 30

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Scientific Calculator - Minor Project")
        self.root.resizable(False, False)
        # Center window
        width, height = 420, 560
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 3
        root.geometry(f"{width}x{height}+{x}+{y}")

        self.expr_var = tk.StringVar()

        self._build_ui()
        self._bind_keys()

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, bg="#222831")
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)


        entry_font = ("Segoe UI", 24)
        display = tk.Entry(
            frame,
            textvariable=self.expr_var,
            font=entry_font,
            bd=0,
            bg="#393E46",
            fg="#EEEEEE",
            justify=tk.RIGHT,
            insertwidth=0,
        )
        display.pack(fill=tk.X, ipady=18, pady=(0, 12))
        display.configure(state="normal")
        self.display = display

        btn_cfg = dict(
            font=("Segoe UI", 14),
            bd=0,
            fg="#222831",
            relief=tk.FLAT,
            activebackground="#00ADB5",
            bg="#EEEEEE",
        )

        # Buttons layout
        buttons = [
            ["AC", "DEL", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "-"],
            ["1", "2", "3", "+"],
            ["!", "0", ".", "^"],
            ["(", ")", "π", "e"],
            ["sin", "cos", "tan", "sqrt"],
            ["log10", "ln", "sqr", "="],
        ]

        grid = tk.Frame(frame, bg="#222831")
        grid.pack(fill=tk.BOTH, expand=True)

        for r, row in enumerate(buttons):
            for c, char in enumerate(row):
                cfg = btn_cfg.copy()
                if char == "=":
                    cfg.update(bg="#00ADB5", fg="#ffffff", font=("Segoe UI", 16, "bold"))
                btn = tk.Button(grid, text=char, command=lambda ch=char: self.on_button(ch), **cfg)
                btn.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

                # increase button padding for better sizing
                btn.configure(padx=6, pady=12)

        # Make grid expand evenly
        for i in range(len(buttons)):
            grid.rowconfigure(i, weight=1)
        for j in range(4):
            grid.columnconfigure(j, weight=1)

    def on_button(self, key: str) -> None:
        expr = self.expr_var.get()
        if key == "AC":
            self.expr_var.set("")
            return
        if key == "DEL":
            # If currently showing an error message, clear full display
            if expr.startswith("Error"):
                self.expr_var.set("")
                return
            if self.display.selection_present():
                start = self.display.index("sel.first")
                end = self.display.index("sel.last")
                self.display.delete(start, end)
                self.display.icursor(start)
            else:
                pos = self.display.index(tk.INSERT)
                if pos > 0:
                    self.display.delete(pos - 1)
                    self.display.icursor(pos - 1)
            return
        if key == "=":
            self._calculate()
            return
        if key == "!":
            self._apply_factorial()
            return
        if key in ("sin", "cos", "tan", "sqrt", "log10", "ln"):
            insert_pos = self.display.index("sel.first") if self.display.selection_present() else self.display.index(tk.INSERT)
            left_text = self.display.get()[:insert_pos]
            if left_text.endswith(f"{key}("):
                return
            self._insert(f"{key}(")
            return
        if key == "π":
            self._insert("pi")
            return
        if key == "e":
            self._insert("e")
            return
        if key == "sqr":
            self._insert("**2")
            return
        # Map symbols
        mapping = {"×": "*", "÷": "/", "^": "^"}
        self._insert(mapping.get(key, key))

    def _apply_factorial(self) -> None:
        s = self.expr_var.get()
        if not s:
            return
        import re

        # If currently showing an error, clear instead
        if s.startswith("Error"):
            self.expr_var.set("")
            return

        # Find an integer at the end of the expression (not part of a decimal)
        m = re.search(r"(?<![\d.])(-?\d+)$", s)
        if not m:
            self.expr_var.set("Error")
            return
        try:
            n = int(m.group(1))
        except Exception:
            self.expr_var.set("Error")
            return
        if n < 0:
            self.expr_var.set("Error")
            return
        try:
            res = math.factorial(n)
        except Exception:
            self.expr_var.set("Error")
            return
        # replace the matched integer with result
        new = s[: m.start(1)] + str(res)
        self.expr_var.set(new)

    def _insert(self, value: str) -> None:
        # Central insertion point that validates operator sequences and decimals
        cur = self.expr_var.get()
        # Prevent overflow
        if len(cur) + len(value) > self.MAX_DISPLAY:
            return

        try:
            sel_start = self.display.index("sel.first")
            sel_end = self.display.index("sel.last")
        except tk.TclError:
            sel_start = self.display.index(tk.INSERT)
            sel_end = sel_start

        if len(value) > 1:
            self.display.delete(sel_start, sel_end)
            self.display.insert(sel_start, value)
            self.display.icursor(sel_start + len(value))
            return

        ch = value
        # Operators set
        ops = "+-*/^%"
        left = cur[:sel_start]
        right = cur[sel_end:]

        if ch == ".":
            # prevent multiple decimals in the current number
            import re

            m = re.search(r"(\d*\.?\d*)$", left)
            last = m.group(1) if m else ""
            if "." in last:
                return
            self.display.delete(sel_start, sel_end)
            self.display.insert(sel_start, ch)
            self.display.icursor(sel_start + 1)
            return

        if ch in ops:
            if not cur and ch != "-":
                return
            while left and left[-1] in ops:
                left = left[:-1]
                sel_start -= 1
            self.display.delete(0, tk.END)
            self.display.insert(0, left + ch + right)
            self.display.icursor(sel_start + 1)
            return

        self.display.delete(sel_start, sel_end)
        self.display.insert(sel_start, ch)
        self.display.icursor(sel_start + 1)

    def _calculate(self) -> None:
        expr = self.expr_var.get()
        try:
            result = safe_eval(expr)
        except Exception:
            self.expr_var.set("Error")
            return

        # Format result reasonably
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        self.expr_var.set(str(result))

    def _bind_keys(self) -> None:
        self.display.bind("<KeyPress>", self._on_key)

    def _on_key(self, event: tk.Event) -> str | None:
        key = event.keysym
        char = event.char
        if key in ("Return", "KP_Enter"):
            self._calculate()
            return "break"
        if key == "BackSpace":
            cur = self.display.get()
            if cur.startswith("Error"):
                self.expr_var.set("")
                return "break"
            if self.display.selection_present():
                start = self.display.index("sel.first")
                end = self.display.index("sel.last")
                self.display.delete(start, end)
                self.display.icursor(start)
            else:
                pos = self.display.index(tk.INSERT)
                if pos > 0:
                    self.display.delete(pos - 1)
                    self.display.icursor(pos - 1)
            return "break"
        if key == "Escape":
            self.expr_var.set("")
            return "break"
        if not char:
            return None
        if char.isalpha():
            return "break"
        if char in "0123456789.+-*/()%^":
            self._insert(char)
            return "break"
        return "break"


def main() -> None:
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
