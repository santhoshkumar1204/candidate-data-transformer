"""Generate synthetic candidate datasets with realistic cross-source inconsistencies."""

from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import phonenumbers
from dateutil.relativedelta import relativedelta


DEFAULT_OUTPUT_DIR = Path("datasets")

COMPANIES = [
    "Google",
    "Microsoft",
    "Amazon",
    "Adobe",
    "Cisco",
    "IBM",
    "Oracle",
    "Zoho",
    "Freshworks",
    "Salesforce",
    "Bluestock",
    "Accenture",
    "Infosys",
    "TCS",
    "Wipro",
]

COMPANY_VARIANTS = {
    "Google": ["Google India", "GOOGLE", "Google LLC"],
    "Microsoft": ["MSFT", "Microsoft India", "MICROSOFT"],
    "Amazon": ["Amazon India", "AWS", "AMZN"],
    "Adobe": ["Adobe Systems", "ADBE", "Adobe India"],
    "Cisco": ["Cisco Systems", "CISCO", "Cisco India"],
    "IBM": ["IBM India", "International Business Machines"],
    "Oracle": ["Oracle India", "ORCL"],
    "Zoho": ["Zoho Corp", "ZOHO"],
    "Freshworks": ["Freshworks Inc", "FreshWorks", "Freshworks Chennai"],
    "Salesforce": ["SFDC", "Salesforce India"],
    "Bluestock": ["BlueStock", "Bluestock Fintech"],
    "Accenture": ["ACN", "Accenture India"],
    "Infosys": ["INFY", "Infosys Ltd"],
    "TCS": ["Tata Consultancy Services", "TCS Ltd"],
    "Wipro": ["Wipro Technologies", "WIPRO"],
}

UNIVERSITIES = [
    "SSN",
    "Anna University",
    "VIT",
    "SRM",
    "PSG",
    "BITS Pilani",
    "IIT Madras",
    "NIT Trichy",
    "IIIT Hyderabad",
]

SKILLS = [
    "Python",
    "Java",
    "React",
    "Django",
    "FastAPI",
    "Spring Boot",
    "AWS",
    "Docker",
    "Kubernetes",
    "TensorFlow",
    "PyTorch",
    "Power BI",
    "SQL",
    "MongoDB",
    "PostgreSQL",
]

SKILL_VARIANTS = {
    "Python": ["python", "Python3", "Py"],
    "Java": ["JAVA", "Core Java"],
    "React": ["React.js", "react"],
    "Django": ["django"],
    "FastAPI": ["Fast API", "fastapi"],
    "Spring Boot": ["SpringBoot", "spring boot"],
    "AWS": ["Amazon Web Services", "aws"],
    "Docker": ["docker"],
    "Kubernetes": ["K8s", "kubernetes"],
    "TensorFlow": ["Tensorflow", "TF"],
    "PyTorch": ["Pytorch", "torch"],
    "Power BI": ["PowerBI", "power bi"],
    "SQL": ["sql", "MySQL"],
    "MongoDB": ["Mongo DB", "mongodb"],
    "PostgreSQL": ["Postgres", "postgresql"],
}

FIRST_NAMES = [
    "Aarav",
    "Vivaan",
    "Aditya",
    "Arjun",
    "Sai",
    "Ishaan",
    "Rohan",
    "Karthik",
    "Rahul",
    "Vikram",
    "Ananya",
    "Diya",
    "Isha",
    "Kavya",
    "Meera",
    "Nisha",
    "Priya",
    "Sneha",
    "Aishwarya",
    "Pooja",
]

LAST_NAMES = [
    "Sharma",
    "Iyer",
    "Nair",
    "Reddy",
    "Menon",
    "Krishnan",
    "Subramanian",
    "Gupta",
    "Patel",
    "Rao",
    "Srinivasan",
    "Narayanan",
    "Chakraborty",
    "Kulkarni",
    "Verma",
]

NICKNAMES = {
    "Aarav": "Aaru",
    "Vivaan": "Viv",
    "Aditya": "Adi",
    "Arjun": "Arj",
    "Karthik": "Karthi",
    "Rahul": "Rahul R.",
    "Vikram": "Vik",
    "Ananya": "Anu",
    "Kavya": "Kavi",
    "Meera": "Meera M.",
    "Priya": "Pri",
    "Sneha": "Sne",
    "Aishwarya": "Aishu",
}

TITLES = [
    "Software Engineer",
    "Senior Software Engineer",
    "Backend Engineer",
    "Frontend Developer",
    "Full Stack Engineer",
    "Data Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Engineering Manager",
    "BI Analyst",
]

DEGREES = ["B.Tech", "M.Tech", "B.E.", "MCA", "M.Sc Computer Science"]
LOCATIONS = ["Chennai", "Bengaluru", "Hyderabad", "Pune", "Mumbai", "Delhi NCR", "Coimbatore"]
EMAIL_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "proton.me", "hotmail.com"]
BAD_EMAIL_DOMAINS = ["gamil.com", "gnail.com", "outlok.com", "yaho.com"]
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%b %d, %Y", "%m/%d/%Y"]


@dataclass
class EdgeTracker:
    duplicate_candidate_ids: list[str] = field(default_factory=list)
    nickname_cases: list[str] = field(default_factory=list)
    company_conflicts: list[str] = field(default_factory=list)
    date_format_conflicts: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    multiple_phone_numbers: list[str] = field(default_factory=list)
    old_new_company_conflicts: list[str] = field(default_factory=list)
    other_edge_cases: dict[str, int] = field(default_factory=dict)

    def bump(self, name: str) -> None:
        self.other_edge_cases[name] = self.other_edge_cases.get(name, 0) + 1


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "candidate"


def make_email(first_name: str, last_name: str, index: int, rng: random.Random) -> str:
    separator = rng.choice([".", "_", ""])
    domain = rng.choice(EMAIL_DOMAINS)
    return f"{first_name.lower()}{separator}{last_name.lower()}{index % 97}@{domain}"


def corrupt_email(email: str, rng: random.Random) -> str:
    local, _, _domain = email.partition("@")
    choice = rng.choice(["missing_at", "bad_domain", "space"])
    if choice == "missing_at":
        return email.replace("@", "", 1)
    if choice == "space":
        return f" {email} "
    return f"{local}@{rng.choice(BAD_EMAIL_DOMAINS)}"


def make_phone(index: int) -> str:
    number = 7000000000 + ((index * 7919) % 1999999999)
    return str(number)


def format_phone(phone: str, rng: random.Random) -> str:
    formats = [
        phone,
        f"+91 {phone[:5]} {phone[5:]}",
        f"0{phone}",
        f"({phone[:3]}) {phone[3:6]}-{phone[6:]}",
        f"+91-{phone[:5]}-{phone[5:]}",
    ]
    return rng.choice(formats)


def corrupt_phone(phone: str, rng: random.Random) -> str:
    choice = rng.choice(["too_short", "letters", "too_long"])
    if choice == "too_short":
        return phone[:7]
    if choice == "letters":
        return f"+91 {phone[:5]} ABCDE"
    return f"{phone}{rng.randint(100, 999)}"


def is_valid_email(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value.strip()))


def is_valid_phone(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    pieces = re.split(r"[,;/]", value)
    for piece in pieces:
        try:
            parsed = phonenumbers.parse(piece.strip(), "IN")
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_valid_number(parsed):
            return True
    return False


def random_date(rng: random.Random, years_back: int = 2) -> date:
    start = date.today() - relativedelta(years=years_back)
    days = (date.today() - start).days
    return start + timedelta(days=rng.randint(0, days))


def format_date(value: date, rng: random.Random) -> str:
    return value.strftime(rng.choice(DATE_FORMATS))


def choose_skills(rng: random.Random) -> tuple[str, str]:
    primary = rng.sample(SKILLS, rng.randint(3, 5))
    remaining = [skill for skill in SKILLS if skill not in primary]
    secondary = rng.sample(remaining, rng.randint(2, 4))
    return ", ".join(primary), ", ".join(secondary)


def maybe_variant(value: str, variants: dict[str, list[str]], rng: random.Random) -> str:
    if value in variants and rng.random() < 0.45:
        return rng.choice(variants[value])
    return value


def build_base_record(index: int, rng: random.Random, tracker: EdgeTracker) -> dict[str, Any]:
    first_name = rng.choice(FIRST_NAMES)
    last_name = rng.choice(LAST_NAMES)
    full_name = f"{first_name} {last_name}"
    company = rng.choice(COMPANIES)
    title = rng.choice(TITLES)
    years_experience = rng.randint(1, 14)
    current_ctc = round(rng.uniform(6, 45), 1)
    expected_ctc = round(current_ctc * rng.uniform(1.15, 1.55), 1)
    primary_skills, secondary_skills = choose_skills(rng)
    graduation_year = datetime.now().year - years_experience - rng.randint(1, 4)
    phone = format_phone(make_phone(index), rng)
    email = make_email(first_name, last_name, index, rng)
    linkedin_slug = slugify(full_name)
    github_slug = slugify(f"{first_name}{last_name}{index % 31}")

    record = {
        "candidate_id": f"CAND-{index:04d}",
        "full_name": full_name,
        "primary_email": email,
        "phone_number": phone,
        "current_company": company,
        "current_title": title,
        "years_experience": years_experience,
        "highest_degree": rng.choice(DEGREES),
        "university": rng.choice(UNIVERSITIES),
        "graduation_year": graduation_year,
        "primary_skills": primary_skills,
        "secondary_skills": secondary_skills,
        "current_location": rng.choice(LOCATIONS),
        "preferred_location": rng.choice(LOCATIONS),
        "current_ctc_lpa": current_ctc,
        "expected_ctc_lpa": expected_ctc,
        "notice_period_days": rng.choice([0, 15, 30, 45, 60, 90]),
        "linkedin_url": f"https://www.linkedin.com/in/{linkedin_slug}-{index}",
        "github_url": f"https://github.com/{github_slug}",
        "recruiter_notes": rng.choice(
            [
                "Strong system design fundamentals.",
                "Interested in product engineering roles.",
                "Open to Bengaluru and Chennai.",
                "Needs compensation discussion.",
                "Good communication, prefers backend work.",
                "Actively interviewing with multiple companies.",
            ]
        ),
        "last_updated": format_date(random_date(rng), rng),
    }

    if index % 17 == 0:
        record["full_name"] = record["full_name"].upper()
        tracker.bump("uppercase_names")
    if index % 19 == 0:
        record["full_name"] = f"  {record['full_name']}  "
        tracker.bump("extra_whitespace_names")
    if index % 23 == 0:
        nickname_source = first_name if first_name in NICKNAMES else rng.choice(list(NICKNAMES))
        record["full_name"] = f"{NICKNAMES[nickname_source]} {last_name}"
        tracker.nickname_cases.append(record["candidate_id"])
    if index % 13 == 0:
        record["primary_email"] = ""
    if index % 29 == 0:
        record["primary_email"] = corrupt_email(email, rng)
    if index % 11 == 0:
        record["phone_number"] = ""
    if index % 31 == 0:
        record["phone_number"] = corrupt_phone(make_phone(index), rng)
    if index % 37 == 0:
        extra_phone = format_phone(make_phone(index + 1000), rng)
        record["phone_number"] = f"{phone}, {extra_phone}"
        tracker.multiple_phone_numbers.append(record["candidate_id"])
    if index % 16 == 0:
        record["current_company"] = maybe_variant(company, COMPANY_VARIANTS, rng)
        tracker.company_conflicts.append(record["candidate_id"])
    if index % 21 == 0:
        record["primary_skills"] = ""
        tracker.missing_skills.append(record["candidate_id"])
    if index % 27 == 0:
        record["graduation_year"] = ""
        tracker.bump("missing_graduation_year")
    if index % 14 == 0:
        tracker.date_format_conflicts.append(record["candidate_id"])

    return record


def duplicate_record(source: dict[str, Any], index: int, rng: random.Random, tracker: EdgeTracker) -> dict[str, Any]:
    record = dict(source)
    record["candidate_id"] = f"CAND-{index:04d}"
    name = str(record["full_name"]).strip()
    parts = name.split()
    if len(parts) >= 2:
        if parts[0] in NICKNAMES:
            parts[0] = NICKNAMES[parts[0]]
            tracker.nickname_cases.append(record["candidate_id"])
        else:
            parts.insert(1, rng.choice(["K.", "S.", "R."]))
        record["full_name"] = " ".join(parts)
    record["phone_number"] = format_phone(re.sub(r"\D", "", str(record["phone_number"]))[-10:] or make_phone(index), rng)
    if record.get("primary_email"):
        record["primary_email"] = str(record["primary_email"]).replace("@", f"+alt{index}@")
    record["current_company"] = rng.choice(COMPANIES)
    record["last_updated"] = format_date(random_date(rng), rng)
    record["recruiter_notes"] = "Possible duplicate from alternate recruiter intake."
    tracker.duplicate_candidate_ids.append(record["candidate_id"])
    tracker.old_new_company_conflicts.append(record["candidate_id"])
    return record


def generate_recruiter_records(count: int, rng: random.Random) -> tuple[list[dict[str, Any]], EdgeTracker]:
    tracker = EdgeTracker()
    records: list[dict[str, Any]] = []
    duplicate_indexes = set(rng.sample(range(8, count + 1), k=max(1, count // 12))) if count >= 8 else set()

    for index in range(1, count + 1):
        if index in duplicate_indexes and records:
            source = rng.choice(records[: max(1, len(records) - 1)])
            records.append(duplicate_record(source, index, rng, tracker))
        else:
            records.append(build_base_record(index, rng, tracker))

    return records, tracker


def transform_skills_for_ats(skills: str, rng: random.Random) -> list[str]:
    if not skills:
        return []
    transformed = []
    for skill in [item.strip() for item in skills.split(",") if item.strip()]:
        transformed.append(maybe_variant(skill, SKILL_VARIANTS, rng))
    return transformed


def generate_ats_records(recruiter_records: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    ats_records = []
    for idx, record in enumerate(recruiter_records, start=1):
        company = str(record["current_company"]).strip()
        if company in COMPANY_VARIANTS and idx % 3 == 0:
            company = rng.choice(COMPANY_VARIANTS[company])

        ats_record = {
            "applicantId": record["candidate_id"].replace("CAND", "ATS"),
            "legalName": str(record["full_name"]).strip(),
            "emailAddress": record["primary_email"] if idx % 9 != 0 else None,
            "mobile": format_phone(re.sub(r"\D", "", str(record["phone_number"]))[-10:] or make_phone(idx), rng)
            if idx % 7 != 0
            else None,
            "employer": company,
            "jobTitle": record["current_title"],
            "totalExperienceYears": record["years_experience"],
            "degree": record["highest_degree"],
            "college": record["university"] if idx % 10 != 0 else None,
            "gradYear": record["graduation_year"] if idx % 8 != 0 else None,
            "skills": transform_skills_for_ats(
                f"{record.get('primary_skills', '')}, {record.get('secondary_skills', '')}", rng
            )
            if idx % 11 != 0
            else [],
            "location": record["current_location"],
            "preferredCity": record["preferred_location"],
            "currentCompensationLpa": record["current_ctc_lpa"],
            "expectedCompensationLpa": record["expected_ctc_lpa"],
            "noticePeriod": f"{record['notice_period_days']} days",
            "profileLinks": {
                "linkedin": record["linkedin_url"] if idx % 13 != 0 else "",
                "github": record["github_url"] if idx % 17 != 0 else "",
            },
            "atsStatus": rng.choice(["New", "Screened", "Interviewing", "Offer", "On Hold"]),
            "sourceSystem": rng.choice(["Greenhouse Export", "Lever Import", "Internal ATS"]),
            "profileScore": rng.randint(55, 98),
            "tags": rng.sample(["backend", "frontend", "cloud", "data", "urgent", "relocation"], rng.randint(1, 3)),
            "updatedAt": format_date(random_date(rng), rng),
        }
        if idx % 15 == 0:
            ats_record["previousEmployer"] = record["current_company"]
            ats_record["employer"] = rng.choice([company for company in COMPANIES if company != record["current_company"]])
        ats_records.append(ats_record)
    return ats_records


def linkedin_text(record: dict[str, Any], rng: random.Random, incomplete: bool) -> str:
    name = str(record["full_name"]).strip()
    company = str(record["current_company"]).strip()
    title = record["current_title"]
    skills = ", ".join(
        item.strip()
        for item in f"{record.get('primary_skills', '')}, {record.get('secondary_skills', '')}".split(",")
        if item.strip()
    )

    sections = [
        f"Headline\n{name} - {title} at {company}",
        (
            "About\n"
            f"{name} is a software professional based in {record['current_location']} with "
            f"{record['years_experience']} years of experience. Preferred location: {record['preferred_location']}."
        ),
        (
            "Experience\n"
            f"{title}, {maybe_variant(company, COMPANY_VARIANTS, rng)}\n"
            f"Worked on scalable platforms, APIs, cloud services, and product engineering initiatives."
        ),
        f"Education\n{record['highest_degree']} from {record['university']}, class of {record['graduation_year']}.",
        f"Skills\n{skills or 'Not listed'}",
        f"Certifications\n{rng.choice(['AWS Certified Developer', 'Azure Fundamentals', 'Docker Certified Associate', 'Not specified'])}",
        (
            "Projects\n"
            f"Built internal tools using {rng.choice(SKILLS)} and {rng.choice(SKILLS)}. "
            "Improved reporting, deployment reliability, and engineering productivity."
        ),
    ]
    if incomplete:
        keep = rng.sample(sections, k=rng.randint(3, 5))
        return "\n\n".join(keep)
    return "\n\n".join(sections)


def resume_text(record: dict[str, Any], rng: random.Random) -> str:
    name = str(record["full_name"]).strip()
    skills = ", ".join(
        item.strip()
        for item in f"{record.get('primary_skills', '')}, {record.get('secondary_skills', '')}".split(",")
        if item.strip()
    )
    project_skill = rng.choice([skill for skill in SKILLS if skill in skills] or SKILLS)
    return f"""# {name}

## Summary

{record['current_title']} with {record['years_experience']} years of experience across product engineering, data systems, and cloud platforms.

## Education

- {record['highest_degree']}, {record['university']} ({record['graduation_year'] or 'Year not specified'})

## Experience

### {record['current_company']}

- Worked as {record['current_title']} on customer-facing and internal engineering platforms.
- Collaborated with product, QA, and infrastructure teams across distributed releases.
- Improved reliability, observability, and delivery speed for business-critical services.

## Projects

- Candidate Insights Dashboard: built reporting workflows using {project_skill}.
- Deployment Health Monitor: automated release checks and operational alerts.

## Skills

{skills or 'Skills not clearly listed'}

## Achievements

- Recognized for ownership during production releases.
- Mentored junior engineers and improved onboarding documentation.
"""


def write_linkedin_profiles(records: list[dict[str, Any]], output_dir: Path, rng: random.Random) -> int:
    linkedin_dir = output_dir / "linkedin"
    linkedin_dir.mkdir(parents=True, exist_ok=True)
    for old_file in linkedin_dir.glob("*.txt"):
        old_file.unlink()
    incomplete_count = 0
    for idx, record in enumerate(records, start=1):
        incomplete = idx % 9 == 0
        if incomplete:
            incomplete_count += 1
        path = linkedin_dir / f"{record['candidate_id']}_{slugify(str(record['full_name']))}.txt"
        path.write_text(linkedin_text(record, rng, incomplete), encoding="utf-8")
    return incomplete_count


def write_resumes(records: list[dict[str, Any]], output_dir: Path, rng: random.Random) -> int:
    resume_dir = output_dir / "resume"
    resume_dir.mkdir(parents=True, exist_ok=True)
    for old_file in resume_dir.glob("*.md"):
        old_file.unlink()
    sample_size = min(len(records), max(10, min(20, len(records) // 8 or len(records))))
    sampled = rng.sample(records, k=sample_size)
    for record in sampled:
        path = resume_dir / f"{record['candidate_id']}_{slugify(str(record['full_name']))}.md"
        path.write_text(resume_text(record, rng), encoding="utf-8")
    return sample_size


def build_summary(
    records: list[dict[str, Any]],
    tracker: EdgeTracker,
    linkedin_incomplete_count: int,
    resume_count: int,
) -> dict[str, Any]:
    missing_phones = [record["candidate_id"] for record in records if not str(record.get("phone_number", "")).strip()]
    missing_emails = [record["candidate_id"] for record in records if not str(record.get("primary_email", "")).strip()]
    invalid_phones = [
        record["candidate_id"]
        for record in records
        if str(record.get("phone_number", "")).strip() and not is_valid_phone(record.get("phone_number"))
    ]
    invalid_emails = [
        record["candidate_id"]
        for record in records
        if str(record.get("primary_email", "")).strip() and not is_valid_email(record.get("primary_email"))
    ]

    return {
        "number_of_candidates": len(records),
        "duplicates": {
            "count": len(tracker.duplicate_candidate_ids),
            "candidate_ids": tracker.duplicate_candidate_ids,
        },
        "missing_phones": {"count": len(missing_phones), "candidate_ids": missing_phones},
        "missing_emails": {"count": len(missing_emails), "candidate_ids": missing_emails},
        "invalid_phones": {"count": len(invalid_phones), "candidate_ids": invalid_phones},
        "invalid_emails": {"count": len(invalid_emails), "candidate_ids": invalid_emails},
        "nickname_cases": {"count": len(tracker.nickname_cases), "candidate_ids": tracker.nickname_cases},
        "company_conflicts": {"count": len(tracker.company_conflicts), "candidate_ids": tracker.company_conflicts},
        "date_format_conflicts": {
            "count": len(tracker.date_format_conflicts),
            "candidate_ids": tracker.date_format_conflicts,
        },
        "missing_skills": {"count": len(tracker.missing_skills), "candidate_ids": tracker.missing_skills},
        "other_edge_cases": {
            **tracker.other_edge_cases,
            "multiple_phone_numbers": len(tracker.multiple_phone_numbers),
            "old_new_company_conflicts": len(tracker.old_new_company_conflicts),
            "incomplete_linkedin_profiles": linkedin_incomplete_count,
            "generated_resumes": resume_count,
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def generate_dataset(count: int, output_dir: Path, seed: int) -> None:
    if count <= 0:
        raise ValueError("--count must be a positive integer")

    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    recruiter_records, tracker = generate_recruiter_records(count, rng)
    recruiter_path = output_dir / "recruiter.csv"
    pd.DataFrame(recruiter_records).to_csv(recruiter_path, index=False)

    ats_records = generate_ats_records(recruiter_records, rng)
    (output_dir / "ats.json").write_text(json.dumps(ats_records, indent=2), encoding="utf-8")

    linkedin_incomplete_count = write_linkedin_profiles(recruiter_records, output_dir, rng)
    resume_count = write_resumes(recruiter_records, output_dir, rng)

    summary = build_summary(recruiter_records, tracker, linkedin_incomplete_count, resume_count)
    (output_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic candidate datasets.")
    parser.add_argument("--count", type=int, default=100, help="Number of recruiter candidates to generate.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where generated datasets should be written.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for repeatable synthetic data.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_dataset(count=args.count, output_dir=args.output_dir, seed=args.seed)
    print(f"Generated candidate datasets in {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
