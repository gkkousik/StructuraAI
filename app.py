import os, re, json, uuid, base64, string, zlib
import logging, datetime, requests, bcrypt
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']         = os.environ.get('SECRET_KEY', 'structura-dev-secret')
app.config['UPLOAD_FOLDER']      = os.path.join('static', 'diagrams')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ── Database ───────────────────────────────────────────────────────────────────
# Uses PostgreSQL on Render (DATABASE_URL env var set automatically)
# Falls back to SQLite locally — zero code change needed
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    # Render gives postgres:// but SQLAlchemy needs postgresql://
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or \
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'structura.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
GROQ_KEY      = os.environ.get('GROQ_API_KEY', '')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Database Models
# ══════════════════════════════════════════════════════════════════════════════

class User(db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    diagrams   = db.relationship('Diagram', backref='user', lazy=True,
                                 cascade='all, delete-orphan')

class Diagram(db.Model):
    __tablename__ = 'diagrams'
    id           = db.Column(db.String(36), primary_key=True,
                             default=lambda: str(uuid.uuid4()))
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project      = db.Column(db.String(200), nullable=False)
    diagram_type = db.Column(db.String(100), nullable=False)
    theme        = db.Column(db.String(100), default='Default')
    syntax       = db.Column(db.Text, nullable=False)
    image_path   = db.Column(db.String(200), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'username':     self.user.username,
            'project':      self.project,
            'diagram_type': self.diagram_type,
            'theme':        self.theme,
            'syntax':       self.syntax,
            'image_path':   self.image_path,
            'created_at':   self.created_at.isoformat() + 'Z',
        }


# ── Create tables on startup ────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    logger.info("[db] Tables ready — %s",
                app.config['SQLALCHEMY_DATABASE_URI'].split('://')[0])


# ══════════════════════════════════════════════════════════════════════════════
# THEMES — pure skinparam, no !theme, guaranteed readable
# ══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "Classic Blue": """\
skinparam backgroundColor #FFFFFF
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #0D47A1
skinparam ArrowColor #1565C0
skinparam ArrowFontColor #1565C0
skinparam SequenceLifeLineBorderColor #1565C0
skinparam ParticipantBackgroundColor #E3F2FD
skinparam ParticipantBorderColor #1565C0
skinparam ParticipantFontColor #0D47A1
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #BBDEFB
skinparam ActorBorderColor #1565C0
skinparam ActorFontColor #0D47A1
skinparam NoteBackgroundColor #FFF9C4
skinparam NoteBorderColor #F9A825
skinparam ClassBackgroundColor #E3F2FD
skinparam ClassBorderColor #1565C0
skinparam ClassFontColor #0D47A1
skinparam ClassAttributeFontColor #0D47A1
skinparam UsecaseBackgroundColor #E3F2FD
skinparam UsecaseBorderColor #1565C0
skinparam UsecaseFontColor #0D47A1
skinparam ActivityBackgroundColor #E3F2FD
skinparam ActivityBorderColor #1565C0
skinparam ActivityFontColor #0D47A1
skinparam ActivityDiamondBackgroundColor #FFF9C4
skinparam ActivityDiamondBorderColor #F9A825
skinparam ActivityDiamondFontColor #0D47A1
skinparam ComponentBackgroundColor #E3F2FD
skinparam ComponentBorderColor #1565C0
skinparam ComponentFontColor #0D47A1
skinparam NodeBackgroundColor #BBDEFB
skinparam NodeBorderColor #1565C0
skinparam NodeFontColor #0D47A1
skinparam DatabaseBackgroundColor #E3F2FD
skinparam DatabaseBorderColor #1565C0
skinparam DatabaseFontColor #0D47A1
skinparam StateBackgroundColor #E3F2FD
skinparam StateBorderColor #1565C0
skinparam StateFontColor #0D47A1
skinparam EntityBackgroundColor #E3F2FD
skinparam EntityBorderColor #1565C0
skinparam EntityFontColor #0D47A1
skinparam ObjectBackgroundColor #E3F2FD
skinparam ObjectBorderColor #1565C0
skinparam ObjectFontColor #0D47A1
skinparam PackageBackgroundColor #F8FBFF
skinparam PackageBorderColor #1565C0
skinparam PackageFontColor #0D47A1""",

    "Dark Neon": """\
skinparam backgroundColor #0d1117
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #00ff88
skinparam ArrowColor #00ff88
skinparam ArrowFontColor #00ff88
skinparam SequenceLifeLineBorderColor #00ff88
skinparam ParticipantBackgroundColor #161b22
skinparam ParticipantBorderColor #00ff88
skinparam ParticipantFontColor #00ff88
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #161b22
skinparam ActorBorderColor #00ff88
skinparam ActorFontColor #00ff88
skinparam NoteBackgroundColor #1f2937
skinparam NoteBorderColor #ff6b6b
skinparam NoteFontColor #ff6b6b
skinparam ClassBackgroundColor #161b22
skinparam ClassBorderColor #00ff88
skinparam ClassFontColor #00ff88
skinparam ClassAttributeFontColor #c9d1d9
skinparam UsecaseBackgroundColor #161b22
skinparam UsecaseBorderColor #00ff88
skinparam UsecaseFontColor #00ff88
skinparam ActivityBackgroundColor #161b22
skinparam ActivityBorderColor #00ff88
skinparam ActivityFontColor #00ff88
skinparam ActivityDiamondBackgroundColor #1f2937
skinparam ActivityDiamondBorderColor #ff6b6b
skinparam ActivityDiamondFontColor #ff6b6b
skinparam ComponentBackgroundColor #161b22
skinparam ComponentBorderColor #00ff88
skinparam ComponentFontColor #00ff88
skinparam NodeBackgroundColor #1f2937
skinparam NodeBorderColor #00ff88
skinparam NodeFontColor #00ff88
skinparam DatabaseBackgroundColor #161b22
skinparam DatabaseBorderColor #00ff88
skinparam DatabaseFontColor #00ff88
skinparam StateBackgroundColor #161b22
skinparam StateBorderColor #00ff88
skinparam StateFontColor #00ff88
skinparam EntityBackgroundColor #161b22
skinparam EntityBorderColor #00ff88
skinparam EntityFontColor #00ff88
skinparam ObjectBackgroundColor #161b22
skinparam ObjectBorderColor #00ff88
skinparam ObjectFontColor #00ff88
skinparam PackageBackgroundColor #0d1117
skinparam PackageBorderColor #00ff88
skinparam PackageFontColor #00ff88""",

    "Sunset Orange": """\
skinparam backgroundColor #FFF8F0
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #BF360C
skinparam ArrowColor #E65100
skinparam ArrowFontColor #BF360C
skinparam SequenceLifeLineBorderColor #E65100
skinparam ParticipantBackgroundColor #FFE0B2
skinparam ParticipantBorderColor #E65100
skinparam ParticipantFontColor #BF360C
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #FFCCBC
skinparam ActorBorderColor #E65100
skinparam ActorFontColor #BF360C
skinparam NoteBackgroundColor #FFF9C4
skinparam NoteBorderColor #F9A825
skinparam NoteFontColor #BF360C
skinparam ClassBackgroundColor #FFE0B2
skinparam ClassBorderColor #E65100
skinparam ClassFontColor #BF360C
skinparam ClassAttributeFontColor #BF360C
skinparam UsecaseBackgroundColor #FFE0B2
skinparam UsecaseBorderColor #E65100
skinparam UsecaseFontColor #BF360C
skinparam ActivityBackgroundColor #FFE0B2
skinparam ActivityBorderColor #E65100
skinparam ActivityFontColor #BF360C
skinparam ActivityDiamondBackgroundColor #FFCCBC
skinparam ActivityDiamondBorderColor #E65100
skinparam ActivityDiamondFontColor #BF360C
skinparam ComponentBackgroundColor #FFE0B2
skinparam ComponentBorderColor #E65100
skinparam ComponentFontColor #BF360C
skinparam NodeBackgroundColor #FFCCBC
skinparam NodeBorderColor #E65100
skinparam NodeFontColor #BF360C
skinparam DatabaseBackgroundColor #FFE0B2
skinparam DatabaseBorderColor #E65100
skinparam DatabaseFontColor #BF360C
skinparam StateBackgroundColor #FFE0B2
skinparam StateBorderColor #E65100
skinparam StateFontColor #BF360C
skinparam EntityBackgroundColor #FFE0B2
skinparam EntityBorderColor #E65100
skinparam EntityFontColor #BF360C
skinparam ObjectBackgroundColor #FFE0B2
skinparam ObjectBorderColor #E65100
skinparam ObjectFontColor #BF360C
skinparam PackageBackgroundColor #FFF8F0
skinparam PackageBorderColor #E65100
skinparam PackageFontColor #BF360C""",

    "Forest Green": """\
skinparam backgroundColor #F1F8E9
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #1B5E20
skinparam ArrowColor #2E7D32
skinparam ArrowFontColor #1B5E20
skinparam SequenceLifeLineBorderColor #2E7D32
skinparam ParticipantBackgroundColor #C8E6C9
skinparam ParticipantBorderColor #2E7D32
skinparam ParticipantFontColor #1B5E20
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #A5D6A7
skinparam ActorBorderColor #2E7D32
skinparam ActorFontColor #1B5E20
skinparam NoteBackgroundColor #FFFDE7
skinparam NoteBorderColor #F9A825
skinparam NoteFontColor #1B5E20
skinparam ClassBackgroundColor #C8E6C9
skinparam ClassBorderColor #2E7D32
skinparam ClassFontColor #1B5E20
skinparam ClassAttributeFontColor #1B5E20
skinparam UsecaseBackgroundColor #C8E6C9
skinparam UsecaseBorderColor #2E7D32
skinparam UsecaseFontColor #1B5E20
skinparam ActivityBackgroundColor #C8E6C9
skinparam ActivityBorderColor #2E7D32
skinparam ActivityFontColor #1B5E20
skinparam ActivityDiamondBackgroundColor #DCEDC8
skinparam ActivityDiamondBorderColor #558B2F
skinparam ActivityDiamondFontColor #1B5E20
skinparam ComponentBackgroundColor #C8E6C9
skinparam ComponentBorderColor #2E7D32
skinparam ComponentFontColor #1B5E20
skinparam NodeBackgroundColor #A5D6A7
skinparam NodeBorderColor #2E7D32
skinparam NodeFontColor #1B5E20
skinparam DatabaseBackgroundColor #C8E6C9
skinparam DatabaseBorderColor #2E7D32
skinparam DatabaseFontColor #1B5E20
skinparam StateBackgroundColor #C8E6C9
skinparam StateBorderColor #2E7D32
skinparam StateFontColor #1B5E20
skinparam EntityBackgroundColor #C8E6C9
skinparam EntityBorderColor #2E7D32
skinparam EntityFontColor #1B5E20
skinparam ObjectBackgroundColor #C8E6C9
skinparam ObjectBorderColor #2E7D32
skinparam ObjectFontColor #1B5E20
skinparam PackageBackgroundColor #F1F8E9
skinparam PackageBorderColor #2E7D32
skinparam PackageFontColor #1B5E20""",

    "Royal Purple": """\
skinparam backgroundColor #F3E5F5
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #4A148C
skinparam ArrowColor #6A1B9A
skinparam ArrowFontColor #4A148C
skinparam SequenceLifeLineBorderColor #6A1B9A
skinparam ParticipantBackgroundColor #E1BEE7
skinparam ParticipantBorderColor #6A1B9A
skinparam ParticipantFontColor #4A148C
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #CE93D8
skinparam ActorBorderColor #6A1B9A
skinparam ActorFontColor #4A148C
skinparam NoteBackgroundColor #FFF9C4
skinparam NoteBorderColor #F9A825
skinparam NoteFontColor #4A148C
skinparam ClassBackgroundColor #E1BEE7
skinparam ClassBorderColor #6A1B9A
skinparam ClassFontColor #4A148C
skinparam ClassAttributeFontColor #4A148C
skinparam UsecaseBackgroundColor #E1BEE7
skinparam UsecaseBorderColor #6A1B9A
skinparam UsecaseFontColor #4A148C
skinparam ActivityBackgroundColor #E1BEE7
skinparam ActivityBorderColor #6A1B9A
skinparam ActivityFontColor #4A148C
skinparam ActivityDiamondBackgroundColor #CE93D8
skinparam ActivityDiamondBorderColor #6A1B9A
skinparam ActivityDiamondFontColor #4A148C
skinparam ComponentBackgroundColor #E1BEE7
skinparam ComponentBorderColor #6A1B9A
skinparam ComponentFontColor #4A148C
skinparam NodeBackgroundColor #CE93D8
skinparam NodeBorderColor #6A1B9A
skinparam NodeFontColor #4A148C
skinparam DatabaseBackgroundColor #E1BEE7
skinparam DatabaseBorderColor #6A1B9A
skinparam DatabaseFontColor #4A148C
skinparam StateBackgroundColor #E1BEE7
skinparam StateBorderColor #6A1B9A
skinparam StateFontColor #4A148C
skinparam EntityBackgroundColor #E1BEE7
skinparam EntityBorderColor #6A1B9A
skinparam EntityFontColor #4A148C
skinparam ObjectBackgroundColor #E1BEE7
skinparam ObjectBorderColor #6A1B9A
skinparam ObjectFontColor #4A148C
skinparam PackageBackgroundColor #F3E5F5
skinparam PackageBorderColor #6A1B9A
skinparam PackageFontColor #4A148C""",

    "Midnight Dark": """\
skinparam backgroundColor #1a1a2e
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #eaeaea
skinparam ArrowColor #e94560
skinparam ArrowFontColor #e94560
skinparam SequenceLifeLineBorderColor #e94560
skinparam ParticipantBackgroundColor #16213e
skinparam ParticipantBorderColor #e94560
skinparam ParticipantFontColor #eaeaea
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #0f3460
skinparam ActorBorderColor #e94560
skinparam ActorFontColor #eaeaea
skinparam NoteBackgroundColor #0f3460
skinparam NoteBorderColor #f5a623
skinparam NoteFontColor #f5a623
skinparam ClassBackgroundColor #16213e
skinparam ClassBorderColor #e94560
skinparam ClassFontColor #eaeaea
skinparam ClassAttributeFontColor #c0c0c0
skinparam UsecaseBackgroundColor #16213e
skinparam UsecaseBorderColor #e94560
skinparam UsecaseFontColor #eaeaea
skinparam ActivityBackgroundColor #16213e
skinparam ActivityBorderColor #e94560
skinparam ActivityFontColor #eaeaea
skinparam ActivityDiamondBackgroundColor #0f3460
skinparam ActivityDiamondBorderColor #f5a623
skinparam ActivityDiamondFontColor #f5a623
skinparam ComponentBackgroundColor #16213e
skinparam ComponentBorderColor #e94560
skinparam ComponentFontColor #eaeaea
skinparam NodeBackgroundColor #0f3460
skinparam NodeBorderColor #e94560
skinparam NodeFontColor #eaeaea
skinparam DatabaseBackgroundColor #16213e
skinparam DatabaseBorderColor #e94560
skinparam DatabaseFontColor #eaeaea
skinparam StateBackgroundColor #16213e
skinparam StateBorderColor #e94560
skinparam StateFontColor #eaeaea
skinparam EntityBackgroundColor #16213e
skinparam EntityBorderColor #e94560
skinparam EntityFontColor #eaeaea
skinparam ObjectBackgroundColor #16213e
skinparam ObjectBorderColor #e94560
skinparam ObjectFontColor #eaeaea
skinparam PackageBackgroundColor #1a1a2e
skinparam PackageBorderColor #e94560
skinparam PackageFontColor #eaeaea""",

    "Ocean Teal": """\
skinparam backgroundColor #E0F7FA
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #004D40
skinparam ArrowColor #00695C
skinparam ArrowFontColor #004D40
skinparam SequenceLifeLineBorderColor #00695C
skinparam ParticipantBackgroundColor #B2EBF2
skinparam ParticipantBorderColor #00695C
skinparam ParticipantFontColor #004D40
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #80DEEA
skinparam ActorBorderColor #00695C
skinparam ActorFontColor #004D40
skinparam NoteBackgroundColor #FFF8E1
skinparam NoteBorderColor #FF8F00
skinparam NoteFontColor #004D40
skinparam ClassBackgroundColor #B2EBF2
skinparam ClassBorderColor #00695C
skinparam ClassFontColor #004D40
skinparam ClassAttributeFontColor #004D40
skinparam UsecaseBackgroundColor #B2EBF2
skinparam UsecaseBorderColor #00695C
skinparam UsecaseFontColor #004D40
skinparam ActivityBackgroundColor #B2EBF2
skinparam ActivityBorderColor #00695C
skinparam ActivityFontColor #004D40
skinparam ActivityDiamondBackgroundColor #80DEEA
skinparam ActivityDiamondBorderColor #00695C
skinparam ActivityDiamondFontColor #004D40
skinparam ComponentBackgroundColor #B2EBF2
skinparam ComponentBorderColor #00695C
skinparam ComponentFontColor #004D40
skinparam NodeBackgroundColor #80DEEA
skinparam NodeBorderColor #00695C
skinparam NodeFontColor #004D40
skinparam DatabaseBackgroundColor #B2EBF2
skinparam DatabaseBorderColor #00695C
skinparam DatabaseFontColor #004D40
skinparam StateBackgroundColor #B2EBF2
skinparam StateBorderColor #00695C
skinparam StateFontColor #004D40
skinparam EntityBackgroundColor #B2EBF2
skinparam EntityBorderColor #00695C
skinparam EntityFontColor #004D40
skinparam ObjectBackgroundColor #B2EBF2
skinparam ObjectBorderColor #00695C
skinparam ObjectFontColor #004D40
skinparam PackageBackgroundColor #E0F7FA
skinparam PackageBorderColor #00695C
skinparam PackageFontColor #004D40""",

    "Rose Gold": """\
skinparam backgroundColor #FCE4EC
skinparam defaultFontName Arial
skinparam defaultFontSize 13
skinparam defaultFontColor #880E4F
skinparam ArrowColor #C2185B
skinparam ArrowFontColor #880E4F
skinparam SequenceLifeLineBorderColor #C2185B
skinparam ParticipantBackgroundColor #F8BBD9
skinparam ParticipantBorderColor #C2185B
skinparam ParticipantFontColor #880E4F
skinparam ParticipantFontStyle bold
skinparam ActorBackgroundColor #F48FB1
skinparam ActorBorderColor #C2185B
skinparam ActorFontColor #880E4F
skinparam NoteBackgroundColor #FFF9C4
skinparam NoteBorderColor #F9A825
skinparam NoteFontColor #880E4F
skinparam ClassBackgroundColor #F8BBD9
skinparam ClassBorderColor #C2185B
skinparam ClassFontColor #880E4F
skinparam ClassAttributeFontColor #880E4F
skinparam UsecaseBackgroundColor #F8BBD9
skinparam UsecaseBorderColor #C2185B
skinparam UsecaseFontColor #880E4F
skinparam ActivityBackgroundColor #F8BBD9
skinparam ActivityBorderColor #C2185B
skinparam ActivityFontColor #880E4F
skinparam ActivityDiamondBackgroundColor #F48FB1
skinparam ActivityDiamondBorderColor #C2185B
skinparam ActivityDiamondFontColor #880E4F
skinparam ComponentBackgroundColor #F8BBD9
skinparam ComponentBorderColor #C2185B
skinparam ComponentFontColor #880E4F
skinparam NodeBackgroundColor #F48FB1
skinparam NodeBorderColor #C2185B
skinparam NodeFontColor #880E4F
skinparam DatabaseBackgroundColor #F8BBD9
skinparam DatabaseBorderColor #C2185B
skinparam DatabaseFontColor #880E4F
skinparam StateBackgroundColor #F8BBD9
skinparam StateBorderColor #C2185B
skinparam StateFontColor #880E4F
skinparam EntityBackgroundColor #F8BBD9
skinparam EntityBorderColor #C2185B
skinparam EntityFontColor #880E4F
skinparam ObjectBackgroundColor #F8BBD9
skinparam ObjectBorderColor #C2185B
skinparam ObjectFontColor #880E4F
skinparam PackageBackgroundColor #FCE4EC
skinparam PackageBorderColor #C2185B
skinparam PackageFontColor #880E4F""",
}

THEME_NAMES = list(THEMES.keys())

def get_theme_skinparam(theme_name):
    return THEMES.get(theme_name, '')


# ══════════════════════════════════════════════════════════════════════════════
# PlantUML renderer
# ══════════════════════════════════════════════════════════════════════════════

_PU_ALPHA  = string.digits + string.ascii_uppercase + string.ascii_lowercase + '-_'
_B64_ALPHA = string.ascii_uppercase + string.ascii_lowercase + string.digits + '+/'
_TRANS     = bytes.maketrans(_B64_ALPHA.encode(), _PU_ALPHA.encode())

PLANTUML_SERVERS = [
    'http://www.plantuml.com/plantuml/img/',
    'https://www.plantuml.com/plantuml/img/',
    'http://www.plantuml.com/plantuml/png/',
]

def _encode(text):
    return base64.b64encode(zlib.compress(text.encode('utf-8'))[2:-4]).translate(_TRANS).decode()

def render_diagram(syntax):
    full       = syntax.strip() if syntax.strip().startswith('@start') \
                 else f"@startuml\n{syntax}\n@enduml"
    encoded    = _encode(full)
    last_error = 'No server tried'
    for server in PLANTUML_SERVERS:
        url = server + encoded
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                if resp.content[:4] == b'\x89PNG':
                    logger.info("[plantuml] OK via %s (%d B)", server, len(resp.content))
                    return resp.content
                return resp.content
            last_error = f"HTTP {resp.status_code} from {server}"
        except requests.Timeout:
            last_error = f"Timeout on {server}"
        except requests.ConnectionError as e:
            last_error = f"Connection error: {e}"
        except Exception as e:
            last_error = str(e)
    raise RuntimeError(
        f"PlantUML server unreachable. {last_error}. "
        "Check your internet connection and try again."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Syntax cleaner
# ══════════════════════════════════════════════════════════════════════════════

def clean_syntax(raw, theme_skinparam):
    text = raw.strip()
    text = re.sub(r'^```[a-zA-Z]*\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()
    for open_tag, close_tag in [('@startuml', '@enduml'), ('@startmindmap', '@endmindmap')]:
        pat = rf'({re.escape(open_tag)}.*?{re.escape(close_tag)})'
        m   = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            block = m.group(1).strip()
            block = re.sub(r'!theme\s+\S+\n?', '', block)
            block = block.replace('{{', '{').replace('}}', '}')
            if theme_skinparam and open_tag == '@startuml':
                block = block.replace('@startuml', f'@startuml\n{theme_skinparam}', 1)
            return block
    inner = re.sub(r'@start\w+\s*', '', text, flags=re.IGNORECASE)
    inner = re.sub(r'@end\w+\s*', '', inner, flags=re.IGNORECASE)
    inner = re.sub(r'!theme\s+\S+\n?', '', inner)
    inner = inner.replace('{{', '{').replace('}}', '}').strip()
    if not inner:
        raise ValueError("AI returned empty diagram content — please try again.")
    header = f"@startuml\n{theme_skinparam}\n" if theme_skinparam else "@startuml\n"
    return f"{header}{inner}\n@enduml"


# ══════════════════════════════════════════════════════════════════════════════
# Catalogue + Prompts
# ══════════════════════════════════════════════════════════════════════════════

DIAGRAM_TYPES = [
    "Sequence Diagram", "Use Case Diagram", "Class Diagram",
    "Object Diagram", "Activity Diagram", "Component Diagram",
    "Deployment Diagram", "State Diagram", "Timing Diagram",
    "Entity Relationship Diagram",
]

DIAGRAM_PROMPTS = {
"Sequence Diagram":
"""Create a detailed PlantUML Sequence Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
skinparam responseMessageBelowArrow true
actor User
participant "Frontend" as FE
participant "Backend API" as API
participant "Database" as DB
User -> FE : Submit Request
activate FE
FE -> API : POST /resource
activate API
API -> DB : INSERT query
activate DB
DB --> API : Success
deactivate DB
API --> FE : 201 Created
deactivate API
FE --> User : Show confirmation
deactivate FE
@enduml
Make it realistic for 'PROJECT_NAME' with 5-8 participants and messages.""",

"Use Case Diagram":
"""Create a detailed PlantUML Use Case Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
left to right direction
actor "Customer" as customer
actor "Admin" as admin
rectangle "PROJECT_NAME System" {
  usecase "Register Account" as UC1
  usecase "Login" as UC2
  usecase "Browse Catalog" as UC3
  usecase "Place Order" as UC4
  usecase "Track Order" as UC5
  usecase "Manage Products" as UC6
  usecase "Generate Reports" as UC7
}
customer --> UC1
customer --> UC2
customer --> UC3
customer --> UC4
customer --> UC5
admin --> UC2
admin --> UC6
admin --> UC7
UC4 ..> UC2 : include
@enduml
Replace with 6-8 realistic use cases for 'PROJECT_NAME'. Use single braces only.""",

"Class Diagram":
"""Create a detailed PlantUML Class Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
skinparam classAttributeIconSize 0
class UserService {
  -userRepository: UserRepository
  +findById(id: Long): User
  +save(user: User): User
  +delete(id: Long): void
}
class User {
  -id: Long
  -name: String
  -email: String
  +getId(): Long
  +getName(): String
}
interface UserRepository {
  +findById(id: Long): User
  +save(user: User): User
}
UserService --> User : manages
UserService ..|> UserRepository : implements
@enduml
Replace with 5-7 realistic classes for 'PROJECT_NAME'. Use single braces only.""",

"Object Diagram":
"""Create a detailed PlantUML Object Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
object "alice : User" as alice {
  id = 1
  name = "Alice Smith"
  email = "alice@example.com"
}
object "order101 : Order" as order101 {
  id = 101
  status = "PROCESSING"
  total = 299.99
}
object "laptop : Product" as laptop {
  id = 201
  name = "Pro Laptop"
  price = 299.99
}
alice --> order101 : places
order101 --> laptop : contains
@enduml
Replace with realistic objects for 'PROJECT_NAME'. Use single braces only.""",

"Activity Diagram":
"""Create a detailed PlantUML Activity Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
start
:Receive Request;
:Authenticate User;
if (Authenticated?) then (yes)
  :Validate Input Data;
  if (Input Valid?) then (yes)
    :Process Business Logic;
    :Update Database;
    :Send Notification;
    :Return Success Response;
  else (no)
    :Return Validation Error;
  endif
else (no)
  :Return 401 Unauthorized;
endif
stop
@enduml
Replace with a realistic workflow for 'PROJECT_NAME' with 8-12 steps.""",

"Component Diagram":
"""Create a detailed PlantUML Component Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
skinparam componentStyle rectangle
package "Frontend" {
  [Web App] as WEB
  [Mobile App] as MOB
}
package "Backend Services" {
  [API Gateway] as GW
  [Auth Service] as AUTH
  [Business Service] as BIZ
}
package "Data Layer" {
  database "Main Database" as DB
  database "Cache" as CACHE
}
WEB --> GW : HTTPS
MOB --> GW : HTTPS
GW --> AUTH : JWT Validate
GW --> BIZ : Route Request
BIZ --> DB : Read/Write
BIZ --> CACHE : Cache
@enduml
Replace with components for 'PROJECT_NAME'. Use single braces only.""",

"Deployment Diagram":
"""Create a detailed PlantUML Deployment Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
node "User Devices" {
  node "Web Browser" as browser
  node "Mobile Device" as mobile
}
node "Cloud Infrastructure" {
  node "Load Balancer" as lb
  node "Web Server" {
    artifact "frontend.js"
  }
  node "App Server" {
    artifact "backend.jar"
  }
}
node "Database Cluster" {
  database "Primary DB" as primaryDB
  database "Replica DB" as replicaDB
}
browser --> lb : HTTPS
mobile --> lb : HTTPS
lb --> "Web Server" : HTTP
"Web Server" --> "App Server" : API
"App Server" --> primaryDB : JDBC
primaryDB --> replicaDB : Replication
@enduml
Replace with infrastructure for 'PROJECT_NAME'. Use single braces only.""",

"State Diagram":
"""Create a detailed PlantUML State Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
[*] --> Draft : Created
state Draft
state UnderReview {
  [*] --> PendingApproval
  PendingApproval --> Approved : approved
  PendingApproval --> Rejected : rejected
}
state Active
state Completed
state Cancelled
Draft --> UnderReview : Submit
UnderReview --> Active : Approved
UnderReview --> Draft : Rejected
Active --> Completed : Finish
Active --> Cancelled : Cancel
Completed --> [*]
Cancelled --> [*]
@enduml
Replace with realistic states for 'PROJECT_NAME'. Use single braces only.""",

"Timing Diagram":
"""Create a detailed PlantUML Timing Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
robust "Client Browser" as CB
concise "API Server" as API
concise "Database" as DB
@0
CB is Idle
API is Idle
DB is Idle
@50
CB is Sending
@100
CB is Waiting
API is Processing
@150
DB is Querying
@250
DB is Idle
API is Responding
@300
CB is Receiving
API is Idle
@400
CB is Idle
@enduml
Replace with a realistic timeline for 'PROJECT_NAME'.""",

"Entity Relationship Diagram":
"""Create a detailed PlantUML ER Diagram for a project called 'PROJECT_NAME'.
Output ONLY the PlantUML code, starting with @startuml and ending with @enduml.
@startuml
entity "User" as users {
  * user_id : INT <<PK>>
  --
  * username : VARCHAR(50)
  * email : VARCHAR(100)
  created_at : DATETIME
}
entity "Product" as products {
  * product_id : INT <<PK>>
  --
  * name : VARCHAR(100)
  * price : DECIMAL(10,2)
  stock_qty : INT
}
entity "Order" as orders {
  * order_id : INT <<PK>>
  --
  * user_id : INT <<FK>>
  * status : VARCHAR(20)
  * total_amount : DECIMAL(10,2)
  ordered_at : DATETIME
}
entity "OrderItem" as order_items {
  * item_id : INT <<PK>>
  --
  * order_id : INT <<FK>>
  * product_id : INT <<FK>>
  * quantity : INT
  * unit_price : DECIMAL(10,2)
}
users ||--o{ orders : places
orders ||--|{ order_items : contains
products ||--o{ order_items : in
@enduml
Replace with 4-6 realistic entities for 'PROJECT_NAME'. Use single braces only.""",
}


# ══════════════════════════════════════════════════════════════════════════════
# Groq AI
# ══════════════════════════════════════════════════════════════════════════════

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

SYSTEM_PROMPT = (
    "You are a PlantUML expert. Follow the template provided exactly. "
    "Use ONLY single braces { } — never double braces {{ }}. "
    "Do NOT add !theme directives. "
    "Output ONLY valid PlantUML starting with @startuml and ending with @enduml. "
    "No markdown fences, no explanations."
)

def call_groq(project_name, diagram_type):
    if not GROQ_KEY:
        raise RuntimeError("GROQ_API_KEY not set. Add it to your .env file.")
    if not GROQ_KEY.startswith('gsk_'):
        raise RuntimeError("Invalid GROQ_API_KEY — must start with 'gsk_'.")
    template    = DIAGRAM_PROMPTS.get(diagram_type, "")
    user_prompt = template.replace('PROJECT_NAME', project_name)
    headers     = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    last_error  = None
    for model in GROQ_MODELS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "max_tokens": 2048, "temperature": 0.2,
        }
        try:
            logger.info("[groq] model=%s diagram=%s", model, diagram_type)
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=60,
            )
            if resp.status_code == 401:
                raise RuntimeError("Groq API key rejected (401).")
            if resp.status_code == 429:
                raise RuntimeError("Groq rate limit (429). Wait a few seconds.")
            if resp.status_code == 404:
                last_error = f"Model {model} not available"; continue
            if not resp.ok:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"; continue
            text = resp.json()["choices"][0]["message"]["content"]
            logger.info("[groq] success model=%s", model)
            return text
        except RuntimeError: raise
        except requests.Timeout:
            last_error = f"Timeout on {model}"
        except Exception as e:
            last_error = str(e)
    raise RuntimeError(f"All Groq models failed. Last error: {last_error}.")

def generate_ai_syntax(project_name, diagram_type, theme_name):
    raw             = call_groq(project_name, diagram_type)
    theme_skinparam = get_theme_skinparam(theme_name) if theme_name else ''
    block           = clean_syntax(raw, theme_skinparam)
    block           = block.replace('{{', '{').replace('}}', '}')
    return block


# ══════════════════════════════════════════════════════════════════════════════
# Auth helpers
# ══════════════════════════════════════════════════════════════════════════════

def hash_password(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw, hashed):
    try: return bcrypt.checkpw(pw.encode(), hashed.encode())
    except: return False

def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*a, **kw)
    return dec


# ══════════════════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index(): return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('try_app'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user     = User.query.filter_by(username=username).first()
        if user and verify_password(password, user.password):
            session['user_id']  = user.id
            session['username'] = user.username
            session['email']    = user.email
            logger.info("Login: %s", username)
            return redirect(url_for('try_app'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session: return redirect(url_for('try_app'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        if not username or not email or not password:
            error = 'All fields are required.'
        elif password != confirm:
            error = 'Passwords do not match.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif User.query.filter_by(username=username).first():
            error = 'Username already taken.'
        elif User.query.filter_by(email=email).first():
            error = 'Email already registered.'
        else:
            user = User(username=username, email=email,
                        password=hash_password(password))
            db.session.add(user)
            db.session.commit()
            session['user_id']  = user.id
            session['username'] = user.username
            session['email']    = user.email
            logger.info("Signup: %s", username)
            return redirect(url_for('try_app'))
    return render_template('signup.html', error=error)

@app.route('/logout')
def logout():
    username = session.get('username', 'unknown')
    session.clear()
    logger.info("Logout: %s", username)
    return redirect(url_for('index'))

@app.route('/try')
@login_required
def try_app():
    return render_template('generate.html',
        diagram_types=DIAGRAM_TYPES, themes=THEME_NAMES,
        username=session['username'])

@app.route('/history')
@login_required
def history():
    user     = User.query.get(session['user_id'])
    diagrams = Diagram.query.filter_by(user_id=user.id)\
                      .order_by(Diagram.created_at.desc()).limit(100).all()
    return render_template('history.html',
        history=[d.to_dict() for d in diagrams],
        username=session['username'])

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    project_name = request.form.get('project_name', '').strip()
    diagram_type = request.form.get('diagram_type', '').strip()
    theme        = request.form.get('theme', '').strip() or None
    if not project_name or not diagram_type:
        return jsonify({'error': 'Project title and diagram type are required.'}), 400
    if diagram_type not in DIAGRAM_TYPES:
        return jsonify({'error': 'Invalid diagram type.'}), 400
    if theme and theme not in THEME_NAMES:
        theme = None
    try:
        logger.info("[generate] user=%s project=%s type=%s theme=%s",
                    session['username'], project_name, diagram_type, theme)
        syntax    = generate_ai_syntax(project_name, diagram_type, theme)
        png_bytes = render_diagram(syntax)
        b64       = base64.b64encode(png_bytes).decode()
        fname     = f"{uuid.uuid4().hex}.png"
        with open(os.path.join(UPLOAD_FOLDER, fname), 'wb') as f:
            f.write(png_bytes)
        diagram = Diagram(
            user_id      = session['user_id'],
            project      = project_name,
            diagram_type = diagram_type,
            theme        = theme or 'Default',
            syntax       = syntax,
            image_path   = fname,
        )
        db.session.add(diagram)
        db.session.commit()
        return jsonify({'diagram': b64, 'syntax': syntax, 'entry_id': diagram.id})
    except RuntimeError as e:
        logger.error("[generate] %s", e)
        return jsonify({'error': str(e)}), 500
    except ValueError as e:
        logger.error("[generate] %s", e)
        return jsonify({'error': str(e)}), 422
    except Exception as e:
        logger.exception("[generate] %s", e)
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/api/history')
@login_required
def api_history():
    diagrams = Diagram.query.filter_by(user_id=session['user_id'])\
                      .order_by(Diagram.created_at.desc()).limit(50).all()
    return jsonify([d.to_dict() for d in diagrams])

@app.route('/api/history/<entry_id>', methods=['DELETE'])
@login_required
def delete_history_entry(entry_id):
    diagram = Diagram.query.filter_by(id=entry_id,
                                      user_id=session['user_id']).first()
    if not diagram:
        return jsonify({'error': 'Not found.'}), 404
    img = os.path.join(UPLOAD_FOLDER, diagram.image_path)
    if os.path.exists(img): os.remove(img)
    db.session.delete(diagram)
    db.session.commit()
    return jsonify({'deleted': entry_id})

@app.route('/static/diagrams/<path:filename>')
def serve_diagram(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.datetime.utcnow().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            debug=os.environ.get('FLASK_ENV', 'development') == 'development')