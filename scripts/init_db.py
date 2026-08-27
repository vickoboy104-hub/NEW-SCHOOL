import json, os, time
from pathlib import Path
import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
CFG = dict(host=os.getenv('MYSQL_HOST','db'), port=int(os.getenv('MYSQL_PORT','3306')), user=os.getenv('MYSQL_USER','eduanimate'), password=os.getenv('MYSQL_PASSWORD','eduanimate_dev'), database=os.getenv('MYSQL_DATABASE','eduanimate'))

def connect(): return mysql.connector.connect(**CFG)

def wait_db():
    for _ in range(45):
        try:
            c=connect(); c.close(); return
        except mysql.connector.Error: time.sleep(2)
    raise RuntimeError('MySQL did not become ready')

def run_schema(c):
    cur=c.cursor(); sql=(ROOT/'schema.sql').read_text(encoding='utf-8')
    for s in sql.split(';'):
        if s.strip(): cur.execute(s)
    c.commit(); cur.close()

def seed(c):
    cur=c.cursor()
    subjects=[('MAT','Mathematics','Visual explanations of algebra and geometry.','📐'),('PHY','Physics','Animated explanations of motion and forces.','⚛️'),('CHE','Chemistry','Explore atomic structure and reactions visually.','🧪'),('CSC','Computer Science','Learn foundational computing concepts visually.','💻')]
    for row in subjects:
        cur.execute("INSERT INTO subjects(code,name,description,icon,published) VALUES(%s,%s,%s,%s,1) ON DUPLICATE KEY UPDATE name=VALUES(name),description=VALUES(description),icon=VALUES(icon),published=1",row)
    c.commit()
    cur.execute('SELECT code,id FROM subjects'); ids=dict(cur.fetchall())
    topics=[
      ('TOP001','MAT','Pythagoras Theorem','Understand the relationship between sides of a right-angled triangle.','pythagoras',1,"Pythagoras' theorem states that the square of the hypotenuse equals the sum of the squares of the other two sides.",["Applies only to right-angled triangles","The hypotenuse is opposite the right angle","Formula: a² + b² = c²","Useful for finding an unknown side"]),
      ('TOP002','MAT','Quadratic Equations','Factorise a quadratic and identify its roots.','quadratic',2,'A quadratic equation has degree two. Factorisation rewrites it as two linear factors.',["Standard form: ax² + bx + c = 0","Factorisation can reveal the roots","If AB = 0, A = 0 or B = 0","Roots satisfy the equation"]),
      ('TOP003','PHY',"Newton's Third Law",'See action and reaction forces in equal and opposite pairs.','newton3',1,"When one object exerts a force on another, the second exerts an equal force in the opposite direction.",["Forces occur in pairs","Equal magnitude","Opposite directions","They act on different objects"]),
      ('TOP004','CHE','Atomic Structure','Explore protons, neutrons, electrons and the nucleus.','atomic',1,'Atoms contain a small nucleus of protons and neutrons, with electrons in regions around it.',["Protons are positive","Neutrons are neutral","Electrons are negative","Most mass is in the nucleus"]),
      ('TOP005','CSC','Binary Numbers','Understand decimal numbers using only 0 and 1.','binary',1,'Binary is base two. Each position has a power-of-two place value.',["Binary uses 0 and 1","Place values are powers of two","1 means include the place value","1101₂ = 13₁₀"])
    ]
    topic_ids={}
    for code,sc,title,desc,anim,seq,overview,points in topics:
        cur.execute("INSERT INTO topics(topic_code,subject_id,title,description,animation_key,sequence_no,published) VALUES(%s,%s,%s,%s,%s,%s,1) ON DUPLICATE KEY UPDATE subject_id=VALUES(subject_id),title=VALUES(title),description=VALUES(description),animation_key=VALUES(animation_key),sequence_no=VALUES(sequence_no),published=1",(code,ids[sc],title,desc,anim,seq))
        cur.execute('SELECT id FROM topics WHERE topic_code=%s',(code,)); tid=cur.fetchone()[0]; topic_ids[code]=tid
        cur.execute("INSERT INTO lessons(topic_id,overview,key_points_json) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE overview=VALUES(overview),key_points_json=VALUES(key_points_json)",(tid,overview,json.dumps(points)))
    bank={
      'TOP001':[("Which triangle uses Pythagoras' theorem?",'Equilateral','Isosceles','Right-angled','Any triangle','C','It applies to right-angled triangles.'),('Which side is the hypotenuse?','Shortest side','Side opposite right angle','Any vertical side','Base only','B','The hypotenuse is opposite the right angle.'),('Correct formula?','a+b=c','a²+b²=c²','a²-b²=c','ab=c²','B','This is the Pythagorean relationship.'),('If a=3,b=4, c=?','5','6','7','12','A','9+16=25, so c=5.'),('If c=13,a=5,b=?','8','10','12','18','C','169-25=144, so b=12.')],
      'TOP002':[('Highest power in a quadratic?','1','2','3','4','B','Quadratics have degree two.'),('x²+5x+6 factorises to?','(x+1)(x+6)','(x+2)(x+3)','(x-2)(x-3)','(x+5)(x+1)','B','2×3=6 and 2+3=5.'),('If (x+2)(x+3)=0, one root is?','2','3','-2','5','C','x+2=0 gives x=-2.'),('Roots of x²+5x+6=0?','2,3','-2,-3','-1,-6','1,6','B','Set both factors to zero.'),('Property used when a product is zero?','Zero-product','Commutative','Distributive','Pythagoras','A','At least one factor must be zero.')],
      'TOP003':[('Third-law forces are?','Equal and opposite','Unequal and opposite','Equal same direction','Unrelated','A','Equal magnitude and opposite direction.'),('They act on?','Same object','Different objects','No objects','Only moving objects','B','They act on two interacting objects.'),('Push a wall and the wall?','Does nothing','Pushes back','Moves automatically','Loses mass','B','The wall exerts an opposite force.'),('A pushes B with 10N; B pushes A with?','0N','5N','10N opposite','20N same direction','C','Equal and opposite.'),('The pair happens?','At different times','Only after motion','During same interaction','Only on one object','C','The pair exists simultaneously.')],
      'TOP004':[('Positive particle?','Electron','Neutron','Proton','Photon','C','Protons are positive.'),('Neutral particle?','Neutron','Electron','Proton','Ion','A','Neutrons are neutral.'),('Protons and neutrons are in?','Outside atom','Nucleus','Shells only','Light waves','B','They form the nucleus.'),('Electron charge?','Positive','Negative','Neutral','Variable','B','Electrons are negative.'),('Most atomic mass is in?','Electron cloud','Nucleus','Outer shell','Empty space','B','Protons and neutrons carry most mass.')],
      'TOP005':[('Binary digits?','0 and 1','1 and 2','0 to 7','0 to 9','A','Binary uses only 0 and 1.'),('Binary is base?','2','8','10','16','A','Binary is base two.'),('1101₂ in decimal?','11','12','13','14','C','8+4+0+1=13.'),('Place left of 1 in 8,4,2,1?','16','8','4','2','D','It is 2.'),('A bit set to 1 means?','Ignore place','Include place value','Multiply by 10','Delete number','B','The place value contributes to the total.')]
    }
    qn=1
    for code,qs in bank.items():
        for seq,q in enumerate(qs,1):
            cur.execute("INSERT INTO quiz_questions(question_code,topic_id,question,option_a,option_b,option_c,option_d,correct_option,explanation,sequence_no) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE topic_id=VALUES(topic_id),question=VALUES(question),option_a=VALUES(option_a),option_b=VALUES(option_b),option_c=VALUES(option_c),option_d=VALUES(option_d),correct_option=VALUES(correct_option),explanation=VALUES(explanation),sequence_no=VALUES(sequence_no)",(f'Q{qn:03d}',topic_ids[code],*q,seq)); qn+=1
    c.commit(); cur.close()

def main():
    wait_db(); c=connect(); run_schema(c); seed(c); c.close(); print('EduAnimate MySQL database ready.')

if __name__=='__main__': main()
