.mode box

SELECT
    max(s.score1, s.score2, s.score3) score, p.name, p.email, s.session_end
FROM
  sessions s
JOIN
  players p ON s.email = p.email
ORDER BY
  CASE
    WHEN s.score1 >= s.score2 AND s.score1 >= s.score3 THEN s.score1
    WHEN s.score2 >= s.score1 AND s.score2 >= s.score3 THEN s.score2
    ELSE s.score3
  END DESC
LIMIT 100
