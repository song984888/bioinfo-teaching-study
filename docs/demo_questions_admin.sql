-- MySQL dump 10.14  Distrib 5.5.68-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: code_exam_v231
-- ------------------------------------------------------
-- Server version	5.5.68-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `questions`
--
-- WHERE:  created_by='admin' AND review_status='pending' AND is_approved=0

/*!40000 ALTER TABLE `questions` DISABLE KEYS */;
INSERT INTO `questions` (`id`, `topic`, `difficulty`, `question_text`, `sample_answer`, `hints`, `language`, `aiModel`, `is_approved`, `question_type`, `created_at`, `review_status`, `created_by`, `review_comment`, `reviewed_by`, `reviewed_at`) VALUES (2,'蛋白质序列疏水氨基酸统计',2,'输入一条蛋白质序列，去除首尾空白并统一大写，统计疏水氨基酸 A/I/L/M/F/W/V/Y 的数量和比例，同时报告未知字符。空序列时输出错误。','import sys\nseq = \'\'.join(sys.stdin.readline().split()).upper()\nif not seq:\n    print(\'ERROR: empty sequence\')\n    raise SystemExit\nhydrophobic = set(\'AILMFWVY\')\nunknown = sorted(set(seq) - set(\'ACDEFGHIKLMNPQRSTVWY\'))\ncount = sum(aa in hydrophobic for aa in seq)\nprint(\'Hydrophobic:\', count)\nprint(\'Ratio: {:.2f}%\'.format(count * 100 / len(seq)))\nprint(\'Unknown:\', \' \'.join(unknown) if unknown else \'None\')','提示：使用集合判断氨基酸类别，并单独检查非法字符。','python','demo_admin',0,'programming','2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL);
/*!40000 ALTER TABLE `questions` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-31 11:44:14
-- MySQL dump 10.14  Distrib 5.5.68-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: code_exam_v231
-- ------------------------------------------------------
-- Server version	5.5.68-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `theory_questions`
--
-- WHERE:  created_by='admin' AND review_status='pending' AND is_approved=0

/*!40000 ALTER TABLE `theory_questions` DISABLE KEYS */;
INSERT INTO `theory_questions` (`id`, `topic`, `question_type`, `question_text`, `sample_answer`, `grading_criteria`, `difficulty`, `score`, `aiModel`, `is_approved`, `created_at`, `review_status`, `created_by`, `review_comment`, `reviewed_by`, `reviewed_at`) VALUES (2,'程序设计与序列分析','名词解释','解释 GC 含量，并说明其可用于序列分析的一个场景。','GC 含量是序列中 G 和 C 所占的百分比，可用于比较基因组区域组成或辅助判断 PCR 引物特性。','定义 4 分；应用场景 4 分；表达 2 分.',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(3,'生物信息学基础','填空题','DNA 序列中互补于 A 的碱基是 ______，互补于 C 的碱基是 ______。','T；G','每空 5 分，答案完全正确。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(4,'程序设计与序列分析','填空题','在 Python 中，使用 ______ 读取一行文本，使用 ______ 去除首尾空白。','input；strip','每空 5 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(5,'生物信息学基础','判断题','FASTA 文件中的序列行可以包含空格，程序无需清理即可直接统计碱基。','错误。序列行可能包含空白或换行，应先清理再统计。','判断 4 分；解释空白处理原因 6 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(6,'程序设计与序列分析','判断题','GC 含量等于 G 和 C 的数量之和除以序列总长度。','正确。对于合法 DNA 序列，GC%=(G+C)/总长度×100%。','判断 4 分；公式 6 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(7,'生物信息学基础','单选题','下列哪项最适合保存带有序列名称和序列内容的生物序列？\nA. FASTA\nB. CSV\nC. HTML\nD. JPEG','A','选 A 得 10 分，并能说明 FASTA 的基本结构。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(8,'程序设计与序列分析','单选题','统计 DNA 序列 GC 含量前，最重要的预处理是什么？\nA. 删除所有 G\nB. 统一大小写并验证字符\nC. 随机打乱序列\nD. 转换为图片','B','选 B 得 10 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(9,'生物信息学基础','多选题','下列哪些属于 DNA 序列质量检查内容？\nA. 检查非法字符\nB. 统计长度\nC. 计算 GC 含量\nD. 修改物种名称','A、B、C','三项全选 10 分，少选或错选不得分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(10,'程序设计与序列分析','多选题','程序读取序列时，哪些操作有助于提高鲁棒性？\nA. 去除空白\nB. 统一大小写\nC. 检查空输入\nD. 忽略所有错误','A、B、C','三项全选 10 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(11,'生物信息学基础','简答题','简述使用程序统计 DNA 序列碱基频数的基本步骤。','读取输入、清理空白、统一大小写、验证字符、初始化计数器、遍历序列累加 A/C/G/T，最后输出长度和频数。','步骤完整 6 分；验证和边界处理 2 分；表达 2 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(12,'程序设计与序列分析','简答题','为什么在计算 GC 含量前需要检查空序列和非法字符？','空序列会导致除零或无意义结果；非法字符会使分母和计数不符合 DNA 序列定义，因此应报告错误或拒绝处理。','空序列 4 分；非法字符 4 分；处理建议 2 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(13,'生物信息学基础','论述题','论述自动化 DNA 序列质量控制流程应包含哪些环节，并说明每个环节的作用。','应包括输入读取、格式解析、空白清理、字符合法性检查、长度与碱基组成统计、异常报告和结果保存。每一环节都应可追踪，错误数据不能静默进入后续分析。','环节 5 分；作用 3 分；可追踪和异常处理 2 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(14,'程序设计与序列分析','论述题','论述程序设计中“可验证输出”对生物信息学教学题目的重要性。','可验证输出使学生结果能够与标准答案或测试用例比较，便于发现边界错误；题目应明确格式、精度、错误输出和样例，避免只打印固定文本。','概念 3 分；教学价值 4 分；实例 3 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(15,'生物信息学基础','案例分析题','某 DNA 文件混入字符 N 和数字，统计程序仍输出 GC 含量。分析这种做法的风险并提出处理方案。','应先报告非法字符及其位置或数量，再决定拒绝该序列或按题目规则处理 N；不能把非法字符默默计入长度而不提示，因为结果可能失真。','风险 4 分；方案 4 分；错误提示 2 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(16,'程序设计与序列分析','案例分析题','某同学将空序列的 GC 含量输出为 0%，但没有提示输入为空。请评价并改进。','0% 可能掩盖没有数据的事实。应区分空输入和合法但 GC 为 0 的序列，空输入输出错误提示并终止，合法序列才计算比例。','问题识别 4 分；改进逻辑 4 分；边界区分 2 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(17,'生物信息学基础','综合题','设计一个序列统计程序，要求读取 DNA 序列，输出长度、A/C/G/T 频数、GC 含量，并处理空输入和非法字符。说明输入输出和测试边界。','程序应清理输入、统一大小写、验证字符、统计四类碱基，按 GC=(G+C)/长度×100 输出；空输入和非法字符给出错误。测试至少包括正常序列、全 A、空输入和含 N 的序列。','功能 4 分；边界 3 分；输出规范 2 分；测试 1 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL),(18,'程序设计与序列分析','综合题','设计一个蛋白质序列分析任务，统计疏水氨基酸比例并报告未知字符。给出算法和复杂度。','读取并清理序列后统一大写，遍历字符，使用集合判断是否为疏水氨基酸，同时用合法氨基酸集合识别未知字符；时间复杂度 O(n)，空间复杂度 O(k)。','算法 5 分；错误处理 2 分；复杂度 3 分。',2,10,'demo_admin',0,'2026-08-31 03:36:43','pending','admin',NULL,NULL,NULL);
/*!40000 ALTER TABLE `theory_questions` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-31 11:44:14
-- Admin-created pending demo questions only; data-only dump.
