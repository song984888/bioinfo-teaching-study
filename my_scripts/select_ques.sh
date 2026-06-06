
username='songht'
db='code_exam'

mysql -u $username -p -D $db -e "
SELECT 
    id,
    topic,
    question_text,
    sample_answer,
FROM questions 
WHERE id IN (238, 2437)
ORDER BY id;
" | sed 's/\t/","/g; s/^/"/; s/$/"/; s/\n//g' > questions_238_2437.csv
