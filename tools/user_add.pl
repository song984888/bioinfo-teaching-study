#!/usr/bin/perl
use strict;
use warnings;
use DBI;
use Digest::SHA qw(sha256_hex);

# MySQL数据库连接配置
my $db_host = "localhost";
my $db_name = "code_exam";
my $db_user = "songht";
my $db_pass = "songht123";

# 连接数据库
my $dbh = DBI->connect("DBI:mysql:database=$db_name;host=$db_host", $db_user, $db_pass, {
    RaiseError => 1,
    AutoCommit => 0  # 使用事务，确保批量操作的一致性
}) or die "无法连接数据库: $DBI::errstr";

# 读取文件并处理
my $userFile=shift;

open(my $fh, '<:encoding(utf8)', $userFile) or die "无法打开文件 $userFile: $!";
my $header = <$fh>;  # 跳过标题行

my @users;
while (my $line = <$fh>) {
    chomp $line;
    next if /^#/;
    # 解析每行数据（建议格式为: 学号\t姓名\t全拼\t角色）
    my @fields = split(/\s+/, $line);
    
    if (scalar(@fields) >= 2) {
        my $employee_id = $fields[0];
        my $name = $fields[2];  #全拼小写为用户名
        my $role = 'student';  # 默认角色
        
        # 如果有角色字段，使用它
        if (scalar(@fields) >= 4) {
            $role = $fields[3] if $fields[3];
        }
        
        # 密码规则：学号 +123
        my $password = $employee_id . '123';
        
        # 使用 SHA256 哈希密码
        my $password_hash = sha256_hex($password);
        
        push @users, {
            employee_id => $employee_id,
            name => $name,
            role => $role,
           password => $password,      # 保存明文密码用于显示
           password_hash => $password_hash  # 保存哈希密码用于数据库
        };
    }
}
close($fh);

# 准备插入语句
my $insert_sql = qq{
    INSERT INTO users (name, employee_id, role, can_login, password_hash, created_at) 
    VALUES (?, ?, ?, 1, ?, NOW())
};

my $sth = $dbh->prepare($insert_sql);

# 批量插入用户
my $success_count = 0;
my $error_count = 0;

eval {
   foreach my $user (@users) {
        eval {
            $sth->execute(
                $user->{name},
                $user->{employee_id},
                $user->{role},
                $user->{password_hash}  # 存储哈希后的密码
            );
            
           if ($sth->rows > 0) {
                $success_count++;
               print "成功创建用户：$user->{name} ($user->{employee_id}), 密码：$user->{password}\n";
            } else {
                $error_count++;
               print "警告：用户已存在或创建失败：$user->{name} ($user->{employee_id})\n";
            }
        };
        
       if ($@) {
            $error_count++;
            warn "创建用户 $user->{name} 时出错：$@\n";
        }
    }
    
    $dbh->commit();
};

if ($@) {
    $dbh->rollback();
    die "批量操作失败: $@";
}

# 生成密码报告文件
open(my $report_fh, '>>:encoding(utf8)', 'user_passwords.txt') or die "无法创建密码报告文件: $!";
print $report_fh "学号\t姓名\t密码\n";
foreach my $user (@users) {
    print $report_fh "$user->{employee_id}\t$user->{name}\t$user->{password}\n";
}
close($report_fh);

# 清理资源
$sth->finish();
$dbh->disconnect();

print "\n操作完成！\n";
print "成功创建: $success_count 个用户\n";
print "失败/重复: $error_count 个\n";
print "密码已保存到: user_passwords.txt\n";
