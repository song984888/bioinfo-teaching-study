#!/usr/bin/env python3
"""
交互式 MySQL/MariaDB 数据导出工具
支持表选择、字段选择和文件名指定
"""

import pandas as pd
import mysql.connector
import sys
import os
from datetime import datetime
import re

class InteractiveDBExporter:
    def __init__(self):
        self.conn = None
        self.current_db = None
        self.tables = []
        self.selected_table = None
        self.table_columns = []
        self.selected_columns = []
        self.query = ""
        self.output_file = ""
        
        # 数据库配置
        self.db_config = {
            'host': 'localhost',
            'user': 'songht',
            'password': 'songht123',
            'database': 'code_exam',
            'port': 3306,
            'charset': 'utf8mb4'
        }
    
    def connect_database(self):
        """连接数据库"""
        print("\n" + "="*60)
        print("数据库连接配置")
        print("="*60)
        
        # 显示当前配置
        print("当前配置:")
        for key, value in self.db_config.items():
            if key == 'password':
                print(f"  {key}: {'*' * len(value) if value else '(空)'}")
            else:
                print(f"  {key}: {value}")
        
        # 询问是否修改配置
        change = input("\n是否修改数据库配置? (y/n, 默认n): ").strip().lower()
        if change == 'y':
            print("\n请输入新的配置 (直接回车保持当前值):")
            for key in self.db_config.keys():
                if key == 'password':
                    new_value = input(f"  {key} [{'*' * len(self.db_config[key]) if self.db_config[key] else '(空)'}]: ").strip()
                else:
                    new_value = input(f"  {key} [{self.db_config[key]}]: ").strip()
                if new_value:
                    self.db_config[key] = new_value
        
        try:
            print("\n正在连接数据库...")
            self.conn = mysql.connector.connect(**self.db_config)
            
            # 获取当前数据库
            cursor = self.conn.cursor()
            cursor.execute("SELECT DATABASE()")
            self.current_db = cursor.fetchone()[0]
            cursor.close()
            
            print(f"✓ 连接成功! 当前数据库: {self.current_db}")
            return True
        except mysql.connector.Error as err:
            print(f"✗ 连接失败: {err}")
            return False
    
    def list_tables(self):
        """列出数据库中的所有表"""
        if not self.conn:
            print("请先连接数据库!")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # 获取所有表名
            cursor.execute("SHOW TABLES")
            self.tables = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            
            if not self.tables:
                print("数据库中没有表!")
                return False
            
            return True
        except mysql.connector.Error as err:
            print(f"获取表列表失败: {err}")
            return False
    
    def show_tables(self):
        """显示表列表并让用户选择"""
        if not self.tables:
            if not self.list_tables():
                return None
        
        print("\n" + "="*60)
        print(f"数据库 '{self.current_db}' 中的表:")
        print("="*60)
        
        for i, table in enumerate(self.tables, 1):
            print(f"  {i:2d}. {table}")
        
        print(f"  0. 返回")
        
        while True:
            try:
                choice = input("\n请选择表编号 (输入0返回): ").strip()
                if choice == '0':
                    return None
                
                idx = int(choice) - 1
                if 0 <= idx < len(self.tables):
                    self.selected_table = self.tables[idx]
                    return self.selected_table
                else:
                    print(f"无效的选择，请输入 1-{len(self.tables)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
    
    def show_table_structure(self, table_name):
        """显示表结构"""
        if not self.conn:
            print("请先连接数据库!")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # 获取表结构
            cursor.execute(f"DESCRIBE {table_name}")
            columns_info = cursor.fetchall()
            
            # 获取表注释
            cursor.execute(f"""
                SELECT TABLE_COMMENT 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = '{self.current_db}' 
                AND TABLE_NAME = '{table_name}'
            """)
            table_comment = cursor.fetchone()
            
            cursor.close()
            
            # 存储列信息
            self.table_columns = [col[0] for col in columns_info]
            
            # 显示表信息
            print("\n" + "="*60)
            print(f"表: {table_name}")
            if table_comment and table_comment[0]:
                print(f"注释: {table_comment[0]}")
            
            # 显示列信息
            print("-"*60)
            print(f"{'字段名':<20} {'类型':<15} {'允许NULL':<8} {'键':<5} {'默认值':<15} {'额外信息'}")
            print("-"*60)
            
            for col in columns_info:
                field, type_str, null, key, default, extra = col
                print(f"{field:<20} {type_str:<15} {null:<8} {key:<5} {str(default)[:15]:<15} {extra}")
            
            # 获取记录数
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            cursor.close()
            
            print("-"*60)
            print(f"总记录数: {count}")
            
            return True
        except mysql.connector.Error as err:
            print(f"获取表结构失败: {err}")
            return False
    
    def select_columns(self):
        """选择要导出的字段"""
        if not self.table_columns:
            print("请先选择表!")
            return False
        
        print("\n" + "="*60)
        print("选择要导出的字段")
        print("="*60)
        
        # 显示所有字段
        print("可用字段:")
        for i, column in enumerate(self.table_columns, 1):
            print(f"  {i:2d}. {column}")
        
        print("\n选择方式:")
        print("  1. 选择所有字段")
        print("  2. 手动选择字段")
        print("  3. 输入自定义字段列表 (用逗号分隔)")
        print("  0. 返回")
        
        while True:
            choice = input("\n请选择操作 (0-3): ").strip()
            
            if choice == '0':
                return False
            elif choice == '1':
                self.selected_columns = self.table_columns.copy()
                print(f"已选择所有字段 ({len(self.selected_columns)}个)")
                return True
            elif choice == '2':
                return self.manual_select_columns()
            elif choice == '3':
                return self.custom_select_columns()
            else:
                print("无效的选择，请输入 0-3 之间的数字")
    
    def manual_select_columns(self):
        """手动选择字段"""
        print("\n请输入要选择的字段编号 (用逗号分隔，如: 1,3,5): ")
        print("输入 'all' 选择所有字段")
        
        while True:
            selection = input("选择: ").strip()
            
            if selection.lower() == 'all':
                self.selected_columns = self.table_columns.copy()
                print(f"已选择所有字段 ({len(self.selected_columns)}个)")
                return True
            
            try:
                indices = [int(idx.strip()) for idx in selection.split(',') if idx.strip()]
                
                # 验证索引
                valid_indices = []
                for idx in indices:
                    if 1 <= idx <= len(self.table_columns):
                        valid_indices.append(idx)
                    else:
                        print(f"警告: 编号 {idx} 无效，忽略")
                
                if not valid_indices:
                    print("没有选择任何有效字段，请重新选择")
                    continue
                
                self.selected_columns = [self.table_columns[idx-1] for idx in valid_indices]
                print(f"\n已选择 {len(self.selected_columns)} 个字段:")
                for i, col in enumerate(self.selected_columns, 1):
                    print(f"  {i}. {col}")
                
                confirm = input("\n确认选择? (y/n): ").strip().lower()
                if confirm == 'y':
                    return True
                else:
                    print("重新选择...")
            except ValueError:
                print("输入格式错误，请使用逗号分隔的数字")
    
    def custom_select_columns(self):
        """自定义字段列表"""
        print("\n请输入要选择的字段名，用逗号分隔:")
        print("示例: id, name, email, created_at")
        
        while True:
            selection = input("字段列表: ").strip()
            
            if not selection:
                print("字段列表不能为空!")
                continue
            
            # 分割字段名
            columns = [col.strip() for col in selection.split(',')]
            
            # 验证字段是否存在
            valid_columns = []
            invalid_columns = []
            
            for col in columns:
                if col in self.table_columns:
                    valid_columns.append(col)
                else:
                    invalid_columns.append(col)
            
            if invalid_columns:
                print(f"警告: 以下字段不存在: {', '.join(invalid_columns)}")
            
            if not valid_columns:
                print("没有选择任何有效字段，请重新输入")
                continue
            
            self.selected_columns = valid_columns
            print(f"\n已选择 {len(self.selected_columns)} 个有效字段:")
            for i, col in enumerate(self.selected_columns, 1):
                print(f"  {i}. {col}")
            
            confirm = input("\n确认选择? (y/n): ").strip().lower()
            if confirm == 'y':
                return True
            else:
                print("重新输入...")
    
    def build_query(self):
        """构建查询语句"""
        if not self.selected_table or not self.selected_columns:
            return None
        
        # 构建字段列表
        columns_str = ", ".join(self.selected_columns)
        
        # 询问是否添加WHERE条件
        print("\n" + "="*60)
        print("查询条件设置")
        print("="*60)
        print("可以添加 WHERE 条件来过滤数据")
        print("示例: ai_score > 80 AND submitted_at > '2023-01-01'")
        print("直接回车导出所有数据")
        
        where_condition = input("\nWHERE 条件 (可选): ").strip()
        
        # 询问是否添加ORDER BY
        print("\n可以添加 ORDER BY 子句来排序")
        print("示例: submitted_at DESC, ai_score DESC")
        
        order_by = input("ORDER BY (可选): ").strip()
        
        # 询问是否限制记录数
        limit = input("限制记录数 (可选，输入数字): ").strip()
        
        # 构建查询语句
        self.query = f"SELECT {columns_str} FROM {self.selected_table}"
        
        if where_condition:
            self.query += f" WHERE {where_condition}"
        
        if order_by:
            self.query += f" ORDER BY {order_by}"
        
        if limit and limit.isdigit():
            self.query += f" LIMIT {limit}"
        
        print(f"\n生成的查询语句:\n{self.query}")
        
        confirm = input("\n确认查询语句? (y/n): ").strip().lower()
        if confirm == 'y':
            return self.query
        else:
            return None
    
    def preview_query(self):
        """预览查询结果"""
        if not self.query:
            print("没有查询语句!")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # 执行计数查询
            count_query = f"SELECT COUNT(*) FROM ({self.query}) AS subquery"
            cursor.execute(count_query)
            count = cursor.fetchone()[0]
            
            # 获取前5条记录
            preview_query = self.query + " LIMIT 5"
            cursor.execute(preview_query)
            results = cursor.fetchall()
            
            # 获取列名
            column_names = [desc[0] for desc in cursor.description]
            
            cursor.close()
            
            print("\n" + "="*60)
            print("查询预览")
            print("="*60)
            print(f"总记录数: {count}")
            print(f"字段: {', '.join(column_names)}")
            
            if results:
                print("\n前5条记录:")
                # 显示列名
                header = " | ".join([f"{col:<15}" for col in column_names[:3]])  # 只显示前3列
                print(header)
                print("-" * len(header))
                
                for row in results:
                    # 只显示前3列的值
                    row_display = " | ".join([f"{str(val)[:15]:<15}" for val in row[:3]])
                    print(row_display)
            
            return True
        except mysql.connector.Error as err:
            print(f"预览查询失败: {err}")
            return False
    
    def set_output_file(self):
        """设置输出文件名"""
        print("\n" + "="*60)
        print("输出文件设置")
        print("="*60)
        
        # 建议默认文件名
        default_name = f"{self.selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 选择文件格式
        print("\n选择导出格式:")
        print("  1. Excel (.xlsx)")
        print("  2. CSV (.csv)")
        print("  3. JSON (.json)")
        print("  4. 自定义")
        
        while True:
            format_choice = input("选择格式 (1-4): ").strip()
            
            if format_choice == '1':
                default_ext = '.xlsx'
                break
            elif format_choice == '2':
                default_ext = '.csv'
                break
            elif format_choice == '3':
                default_ext = '.json'
                break
            elif format_choice == '4':
                default_ext = input("请输入文件扩展名 (如 .txt, .tsv): ").strip()
                if not default_ext.startswith('.'):
                    default_ext = '.' + default_ext
                break
            else:
                print("无效的选择")
        
        # 输入文件名
        while True:
            filename = input(f"\n输出文件名 [{default_name}{default_ext}]: ").strip()
            
            if not filename:
                filename = f"{default_name}{default_ext}"
            
            # 确保有扩展名
            if '.' not in filename:
                filename += default_ext
            
            # 检查文件是否已存在
            if os.path.exists(filename):
                overwrite = input(f"文件 '{filename}' 已存在，是否覆盖? (y/n): ").strip().lower()
                if overwrite != 'y':
                    continue
            
            self.output_file = filename
            print(f"输出文件: {self.output_file}")
            return True
    
    def export_data(self):
        """导出数据到文件"""
        if not self.query or not self.output_file:
            print("查询语句或输出文件未设置!")
            return False
        
        try:
            print(f"\n正在导出数据到: {self.output_file}")
            
            # 读取数据到DataFrame
            df = pd.read_sql(self.query, self.conn)
            
            if df.empty:
                print("警告: 没有查询到任何数据!")
                return False
            
            # 根据文件扩展名选择导出格式
            file_ext = os.path.splitext(self.output_file)[1].lower()
            
            if file_ext == '.xlsx':
                # 导出到Excel
                df.to_excel(self.output_file, index=False, sheet_name=self.selected_table)
                print(f"✓ Excel文件已创建: {self.output_file}")
                
            elif file_ext == '.csv':
                # 导出到CSV
                df.to_csv(self.output_file, index=False, encoding='utf-8-sig')
                print(f"✓ CSV文件已创建: {self.output_file}")
                
            elif file_ext == '.json':
                # 导出到JSON
                df.to_json(self.output_file, orient='records', force_ascii=False, indent=2)
                print(f"✓ JSON文件已创建: {self.output_file}")
                
            else:
                # 默认使用CSV格式
                print(f"警告: 不支持的文件格式 {file_ext}，使用CSV格式")
                csv_file = os.path.splitext(self.output_file)[0] + '.csv'
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"✓ 数据已导出到: {csv_file}")
                self.output_file = csv_file
            
            # 显示导出统计信息
            print(f"\n导出统计:")
            print(f"  表: {self.selected_table}")
            print(f"  字段数: {len(self.selected_columns)}")
            print(f"  记录数: {len(df)}")
            print(f"  文件大小: {os.path.getsize(self.output_file) / 1024:.2f} KB")
            
            # 显示前几个字段的样本
            print(f"\n数据样本 (前3行):")
            print(df.head(3).to_string())
            
            return True
            
        except Exception as e:
            print(f"导出失败: {e}")
            return False
    
    def run_interactive(self):
        """运行交互式导出流程"""
        print("\n" + "="*60)
        print("交互式 MySQL 数据导出工具")
        print("="*60)
        
        # 1. 连接数据库
        if not self.connect_database():
            return
        
        # 主循环
        while True:
            print("\n" + "="*60)
            print("主菜单")
            print("="*60)
            print("  1. 选择表")
            print("  2. 查看表结构")
            print("  3. 选择字段")
            print("  4. 设置查询条件")
            print("  5. 预览查询结果")
            print("  6. 设置输出文件")
            print("  7. 执行导出")
            print("  8. 重新连接数据库")
            print("  0. 退出")
            
            if self.selected_table:
                print(f"\n当前选择: 表 '{self.selected_table}'")
                if self.selected_columns:
                    print(f"      字段: {len(self.selected_columns)} 个")
                if self.query:
                    print(f"      查询: {self.query[:50]}...")
                if self.output_file:
                    print(f"      输出: {self.output_file}")
            
            choice = input("\n请选择操作 (0-8): ").strip()
            
            if choice == '0':
                print("再见!")
                if self.conn:
                    self.conn.close()
                break
            
            elif choice == '1':
                # 选择表
                table = self.show_tables()
                if table:
                    print(f"已选择表: {table}")
                    # 选择表后重置相关设置
                    self.selected_columns = []
                    self.query = ""
                    self.output_file = ""
            
            elif choice == '2':
                # 查看表结构
                if self.selected_table:
                    self.show_table_structure(self.selected_table)
                else:
                    print("请先选择表!")
            
            elif choice == '3':
                # 选择字段
                if self.selected_table:
                    self.select_columns()
                else:
                    print("请先选择表!")
            
            elif choice == '4':
                # 设置查询条件
                if self.selected_table and self.selected_columns:
                    self.build_query()
                else:
                    print("请先选择表和字段!")
            
            elif choice == '5':
                # 预览查询结果
                if self.query:
                    self.preview_query()
                else:
                    print("请先设置查询条件!")
            
            elif choice == '6':
                # 设置输出文件
                if self.selected_table:
                    self.set_output_file()
                else:
                    print("请先选择表!")
            
            elif choice == '7':
                # 执行导出
                if not self.query:
                    print("请先设置查询条件!")
                    continue
                
                if not self.output_file:
                    print("请先设置输出文件!")
                    continue
                
                self.export_data()
            
            elif choice == '8':
                # 重新连接数据库
                if self.conn:
                    self.conn.close()
                self.selected_table = None
                self.selected_columns = []
                self.query = ""
                self.output_file = ""
                
                if not self.connect_database():
                    break
            
            else:
                print("无效的选择，请输入 0-8 之间的数字")

def main():
    """主函数"""
    # 检查必要的库
    try:
        import pandas as pd
        import mysql.connector
    except ImportError:
        print("缺少必要的库，请使用以下命令安装:")
        print("pip install pandas mysql-connector-python openpyxl")
        return
    
    # 创建导出器实例
    exporter = InteractiveDBExporter()
    
    # 运行交互式界面
    exporter.run_interactive()

if __name__ == "__main__":
    main()
