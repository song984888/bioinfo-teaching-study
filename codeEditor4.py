import asyncio
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import PromptSession
from prompt_toolkit.filters import Condition
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer, PerlLexer
import subprocess
import tempfile
import os

class CodeEditor:
    def __init__(self, language):
        self.language = language
        self.buffer = Buffer()
        self.output_buffer = Buffer()
        self.lexer_cls = PythonLexer if language == "python" else PerlLexer

        # 初始化 KeyBindings 实例
        self.key_bindings = KeyBindings()
        self._setup_keybindings()

        # 行号相关初始化...
        self.line_numbers_control = FormattedTextControl(
            text=self._get_line_numbers_text(self.buffer)
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
            event.app.exit(result=True)

        @confirm_key_bindings.add("n", filter=Condition(lambda: True))
        async def _(event):
            event.app.exit(result=False)

        session = PromptSession()
        answer = await session.prompt_async(message + " (y/n): ", key_bindings=confirm_key_bindings)
        return answer

    async def _run_code(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{self.language}') as temp_file:
            temp_file.write(self.buffer.text)
            temp_file_path = temp_file.name

        try:
            if self.language == "python":
                result = await asyncio.create_subprocess_exec(
                    'python', temp_file_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            elif self.language == "perl":
                result = await asyncio.create_subprocess_exec(
                    'perl', temp_file_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            stdout, stderr = await result.communicate()
            output_text = f"代码:\n{self.buffer.text}\n\n输出:\n{stdout.decode()}\n错误信息:\n{stderr.decode()}"

            # 更新输出窗口的内容
            self.output_buffer.text = output_text

            if stdout:
                self.output_buffer.text = stdout.decode('utf-8')
            if stderr:
                self.output_buffer.text += "\n" + stderr.decode('utf-8')

        except Exception as e:
            self.output_buffer.text = f"Error: {str(e)}"

        finally:
            os.remove(temp_file_path)

    def _get_line_numbers_text(self, buffer):
        return '\n'.join(str(i) for i in range(1, buffer.document.line_count + 1))

    def _refresh_line_numbers(self, _):
        self.line_numbers_control.text = self._get_line_numbers_text(self.buffer)

    async def run(self):
        app = Application(
            layout=Layout(self.editor_layout),
            key_bindings=self.key_bindings,
            full_screen=False
        )
        result = await app.run_async()
        return result

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
        print(result,flush=True)
    else:
        print("\n编辑已取消，代码未保存")


if __name__ == "__main__":
    asyncio.run(main())