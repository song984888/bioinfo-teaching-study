-- Demo questions for the BioInformatics Teaching & Exam System
-- Safe to import repeatedly: records are identified by [DEMO-2026] in question_text.
-- All entries start as pending so approval/rejection/question-bank flows can be tested.

START TRANSACTION;

DELETE FROM theory_questions WHERE question_text LIKE '[DEMO-2026]%';
DELETE FROM questions WHERE question_text LIKE '[DEMO-2026]%';

INSERT INTO theory_questions
(topic, question_type, question_text, sample_answer, grading_criteria, difficulty, score, aiModel, is_approved, review_status, review_comment, reviewed_by, reviewed_at)
VALUES
('DNA与基因组学', '名词解释', '[DEMO-2026] 名词解释：什么是基因组（genome）？', '基因组是一个生物体或细胞器中全部遗传物质的总和，包括编码序列、非编码序列及其组织结构。', '答出“全部遗传物质”得2分；说明包含编码与非编码序列得3分。', 1, 5, 'demo', 0, 'pending', NULL, NULL, NULL),
('DNA与基因组学', '填空题', '[DEMO-2026] 填空：DNA的基本组成单位是______，RNA中的碱基U代表______。', '脱氧核苷酸；尿嘧啶。', '每空2分，术语准确。', 1, 4, 'demo', 0, 'pending', NULL, NULL, NULL),
('DNA与基因组学', '判断题', '[DEMO-2026] 判断：所有突变都会导致蛋白质氨基酸序列改变。', '错误。某些突变发生在非编码区，或为同义突变，不改变氨基酸序列。', '判断正确2分；说明一种合理原因3分。', 2, 5, 'demo', 0, 'pending', NULL, NULL, NULL),
('DNA与基因组学', '单选题', '[DEMO-2026] 单选：下列最适合用于获得长读长DNA序列的技术是？\nA. Sanger测序\nB. Illumina短读长测序\nC. Nanopore测序\nD. PCR扩增', 'C。Nanopore测序可产生长读长。', '选C得5分。', 2, 5, 'demo', 0, 'pending', NULL, NULL, NULL),
('DNA与基因组学', '多选题', '[DEMO-2026] 多选：基因组组装质量评价常关注哪些指标？\nA. N50\nB. BUSCO完整度\nC. 测序深度\nD. 氨基酸颜色', 'A、B、C。', '全对5分；漏选每项扣1分；错选不得分。', 2, 5, 'demo', 0, 'pending', NULL, NULL, NULL),
('DNA与基因组学', '简答题', '[DEMO-2026] 简答：比较短读长和长读长测序在基因组组装中的主要优缺点。', '短读长准确度高、成本较低但难跨越重复区；长读长可跨越重复区、提高连续性，但单条读段错误率或成本可能较高。', '分别说明短读长与长读长的至少一项优点和一项局限，各2分；比较清晰得2分。', 2, 6, 'demo', 0, 'pending', NULL, NULL, NULL),
('DNA与基因组学', '论述题', '[DEMO-2026] 论述：结合重复序列和杂合度，讨论为什么高质量基因组组装通常需要多种测序数据协同。', '应说明重复序列造成组装歧义、杂合度增加图结构复杂性；长读长、短读长和Hi-C等数据分别可帮助跨越重复区、纠错和染色体级别挂载。', '问题分析3分；至少两类数据的作用4分；论证结构3分。', 3, 10, 'demo', 0, 'pending', NULL, NULL, NULL),
('生物信息学应用', '案例分析题', '[DEMO-2026] 案例分析：某研究者获得一个植物基因组草图，N50较低且BUSCO缺失率较高。请提出两项可能原因和两项改进措施。', '可能原因：测序深度不足、重复序列或杂合度高、污染或组装参数不当。改进：补充长读长测序、增加深度、进行去污染/纠错、使用Hi-C优化挂载。', '每个合理原因2分；每项可行措施2分；表达清楚2分。', 3, 10, 'demo', 0, 'pending', NULL, NULL, NULL),
('生物信息学应用', '综合题', '[DEMO-2026] 综合题：给定一组DNA测序项目，请完成：\n(1) 写出从质控到变异注释的四个主要步骤；\n(2) 说明覆盖深度不足可能造成的一个后果；\n(3) 为候选变异设计一种验证方案。', '(1) 质控、比对/组装、变异检测、过滤与注释；(2) 漏检或基因型不可靠；(3) PCR后Sanger测序验证等。', '步骤4分；深度影响2分；验证方案4分。', 3, 10, 'demo', 0, 'pending', NULL, NULL, NULL);

INSERT INTO questions
(topic, difficulty, question_text, sample_answer, hints, language, aiModel, is_approved, review_status, review_comment, reviewed_by, reviewed_at, question_type)
VALUES
('序列统计', 1, '[DEMO-2026] Python：编写函数 gc_content(seq)，忽略大小写，返回DNA序列中G和C所占百分比；空序列返回0。', 'def gc_content(seq):\n    seq = seq.upper()\n    return 0 if not seq else 100 * (seq.count("G") + seq.count("C")) / len(seq)', '先统一大小写；注意空字符串。', 'python', 'demo', 0, 'pending', NULL, NULL, NULL, 'programming'),
('字符串处理', 1, '[DEMO-2026] Perl：读取一行DNA序列，输出其反向互补序列。仅需处理A、T、C、G。', 'my $seq = <STDIN>; chomp $seq;\n$seq = reverse uc $seq;\n$seq =~ tr/ATCG/TAGC/;\nprint "$seq\\n";', '可以先reverse，再用tr完成碱基替换。', 'perl', 'demo', 0, 'pending', NULL, NULL, NULL, 'programming'),
('序列统计', 2, '[DEMO-2026] Java：从标准输入读取多条DNA序列（每行一条），输出最长序列的长度；输入为空时输出0。', 'import java.io.*;\npublic class Main {\n  public static void main(String[] args) throws Exception {\n    BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n    String s; int max = 0;\n    while ((s = br.readLine()) != null) max = Math.max(max, s.trim().length());\n    System.out.println(max);\n  }\n}', '使用BufferedReader循环读取；初始化最大值为0。', 'java', 'demo', 0, 'pending', NULL, NULL, NULL, 'programming'),
('序列统计', 2, '[DEMO-2026] C：读取一个仅含A、T、C、G的DNA序列，输出A、T、C、G各自出现次数。', '#include <stdio.h>\nint main(void) {\n  char s[10001]; int a=0,t=0,c=0,g=0;\n  if (scanf("%10000s", s) != 1) return 0;\n  for (int i=0; s[i]; i++) {\n    if(s[i]==\'A\') a++; else if(s[i]==\'T\') t++;\n    else if(s[i]==\'C\') c++; else if(s[i]==\'G\') g++;\n  }\n  printf("A=%d T=%d C=%d G=%d\\n",a,t,c,g);\n  return 0;\n}', '用循环逐字符统计；确定输出格式。', 'c', 'demo', 0, 'pending', NULL, NULL, NULL, 'programming'),
('FASTA处理', 3, '[DEMO-2026] Python：实现 parse_fasta(text)，返回字典 {header: sequence}。忽略空行，拼接同一条序列的多行内容；若序列行出现在第一个标题前，应抛出ValueError。', 'def parse_fasta(text):\n    result, header = {}, None\n    for line in text.splitlines():\n        line = line.strip()\n        if not line: continue\n        if line.startswith(\'>\'):\n            header = line[1:].strip()\n            result[header] = \"\"\n        elif header is None:\n            raise ValueError("sequence before header")\n        else:\n            result[header] += line\n    return result', '维护当前header；读取到新标题时建立新记录。', 'python', 'demo', 0, 'pending', NULL, NULL, NULL, 'programming'),
('算法', 3, '[DEMO-2026] Java：给定整数数组，返回最长严格递增子序列的长度。要求时间复杂度优于O(n²)。', '使用tails数组维护每个长度对应的最小结尾元素，并通过二分查找更新，整体O(n log n)。', '考虑二分查找和tails数组。', 'java', 'demo', 0, 'pending', NULL, NULL, NULL, 'programming');

COMMIT;

-- After import: sign in as a teacher, visit /teacher/review_questions,
-- and approve selected [DEMO-2026] items to test the question bank.
