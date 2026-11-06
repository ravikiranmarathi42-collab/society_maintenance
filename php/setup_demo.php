<?php
// Run once from the project root: php php/setup_demo.php
require_once __DIR__ . '/config/database.php';
$pdo = db();
$pdo->beginTransaction();
try {
  $users = [
    ['admin','admin@example.com','admin123','admin','Society Administrator','9000000000'],
    ['resident1','resident1@example.com','resident123','resident','Rajesh Sharma','9000000001'],
    ['priya','priya@example.com','resident123','resident','Priya Patel','9000000002'],
  ];
  $ins = $pdo->prepare('INSERT IGNORE INTO users(username,email,password_hash,role,full_name,phone) VALUES(?,?,?,?,?,?)');
  foreach ($users as $u) $ins->execute([$u[0],$u[1],password_hash($u[2], PASSWORD_DEFAULT),$u[3],$u[4],$u[5]]);
  $flats = [['A-101','A',1,'2 BHK',3000,'Occupied'],['A-102','A',1,'2 BHK',3000,'Occupied'],['A-201','A',2,'3 BHK',4500,'Occupied'],['B-101','B',1,'2 BHK',2800,'Vacant']];
  $q=$pdo->prepare('INSERT IGNORE INTO flats(flat_number,building_block,floor,flat_type,maintenance_rate,status) VALUES(?,?,?,?,?,?)');
  foreach($flats as $f)$q->execute($f);
  $residentSeed=[['resident1','Rajesh Sharma','A-101','9000000001','resident1@example.com'],['priya','Priya Patel','A-102','9000000002','priya@example.com']];
  $q=$pdo->prepare('INSERT IGNORE INTO residents(user_id,flat_id,full_name,phone,email,joining_date) VALUES(?,?,?,?,?,CURDATE())');
  foreach($residentSeed as $r){$u=$pdo->prepare('SELECT id FROM users WHERE username=?');$u->execute([$r[0]]);$uid=$u->fetchColumn();$f=$pdo->prepare('SELECT id FROM flats WHERE flat_number=?');$f->execute([$r[2]]);$fid=$f->fetchColumn();if($uid&&$fid)$q->execute([$uid,$fid,$r[1],$r[3],$r[4]]);}
  $adminId=(int)$pdo->query("SELECT id FROM users WHERE username='admin'")->fetchColumn();
  $pdo->prepare("INSERT IGNORE INTO notices(title,message,category,published_date,created_by) VALUES(?,?,?,CURDATE(),?)")->execute(['Welcome to Society Maintenance Management','Use this portal to view maintenance bills, payments, complaints and society notices.','General',$adminId]);
  $pdo->commit();
  echo "Demo data ready. Admin: admin / admin123. Resident: resident1 / resident123.\n";
} catch(Throwable $e) { $pdo->rollBack(); fwrite(STDERR, $e->getMessage()."\n"); exit(1); }
