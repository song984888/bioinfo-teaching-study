import asyncio
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import PromptSession
from prompt_toolkit.filters import Condition
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers import PythonLexer, PerlLexer
import subprocess
import tempfile


class CodeEditor:
    def __init__(self, language):
        self.language = language
        self.buffer = Buffer()
        self.output_buffer = Buffer()
        self.lexer_cls = PythonLexer if language == "python" else PerlLexer

        # 关键修复1：正确初始化 KeyBindings 实例
        self.key_bindings = KeyBindings()
        self._setup_keybindings()

        # 行号相关初始化...
        self.line_numbers_control = FormattedTextControl(
            lambda: [
                ("class:line-number", f"{i + 1:3d} ")
                for i in range(self.buffer.document.line_count)
            ]
        )
        self.buffer.on_text_changed += self._refresh_line_numbers

        self.editor_layout = HSplit([
            self._create_editor_pane(),
            Window(height=1, char="-", style="class:line"),
            Window(
                content=BufferControl(buffer=self.output_buffer),
                height=8
            )
        ])

    def _create_editor_pane(self):
        return VSplit([
            Window(
                width=4,
                content=self.line_numbers_control,
                style="class:line-number",
                dont_extend_width=True
            ),
            Window(
                content=BufferControl(
                    buffer=self.buffer,
                    lexer=PygmentsLexer(self.lexer_cls),
                    focusable=True,
                    include_default_input_processors=False
                )
            )
        ], padding=0)
    def _line_numbers(self):
        return [
            ("class:line-number", f"{i + 1:3d} ")
            for i in range(self.buffer.document.line_count)
        ]

    def _setup_keybindings(self):
        @self.key_bindings.add("c-s")
        async def _(event):
            confirmed = await self._confirm("是否提交代码？")
            if confirmed:
                event.app.exit(result=self.buffer.text)

        @self.key_bindings.add("c-d")
        async def _(event):
            await self._run_code()

        @self.key_bindings.add("c-c")
        async def _(event):
            confirmed = await self._confirm("确定要放弃当前代码吗？")
            if confirmed:
                event.app.exit(result=None)

    async def _confirm(self, message):

        confirm_key_bindings = KeyBindings()

        # 为 'y' 和 'n' 键添加处理函数
        @confirm_key_bindings.add("y", filter=Condition(lambda: True))
        async def _(event):
            event.app.exit(result="y")

        @confirm_key_bindings.add("n", filter=Condition(lambda: True))
        async def _(event):
            event.app.exit(result="n")

        session = PromptSession()
        answer = await session.prompt_async(
            f"{message} (y/N) ",
            key_bindings=confirm_key_bindings
        )
        return answer.lower() == "y"

    async def _run_code(self):
        code = self.buffer.text
        if not code.strip():
            self.output_buffer.text = "错误：没有可执行的代码"
            return

        with tempfile.NamedTemporaryFile(suffix=f".{self.language}", delete=False) as f:
            f.write(code.encode())
            f.flush()

            try:
                if self.language == "python":
                    cmd = ["python3", f.name]
                else:
                    cmd = ["perl", f.name]

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                stdout, stderr = await proc.communicate()
                output = f"输出:\n{stdout.decode()}\n错误:\n{stderr.decode()}"
            except Exception as e:
                output = f"运行错误: {str(e)}"

            self.output_buffer.text = output

    async def run(self):
        app = Application(
            layout=Layout(self.editor_layout),
            key_bindings=self.key_bindings,
            full_screen=True,
            style=Style.from_dict({
                "line-number": "#888888",
                "line": "#444444"
            })
        )
        return await app.run_async()
    def _refresh_line_numbers(self, buffer=None):
        self.line_numbers_control.text = lambda: [
            ("class:line-number", f"{i + 1:3d} ")
            for i in range(self.buffer.document.line_count)
        ]




async def main():
    while True:
        lang = input("请选择编程语言 (python/perl): ").lower()
        if lang in ["python", "perl"]:
            break
        print("无效选项，请重新输入")

    editor = CodeEditor(lang)
    print("\n" + "=" * 40)
    print(f"进入 {lang} 代码编辑器 (Ctrl+S 提交 | Ctrl+D 运行 | Ctrl+C 退出)")
    print("=" * 40 + "\n")

    result = await editor.run()

    if result:
        print("\n代码已提交:")
        print(result)
    else:
        print("\n编辑已取消，代码未保存")


if __name__ == "__main__":
    asyncio.run(main())