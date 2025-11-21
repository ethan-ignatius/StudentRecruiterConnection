from ..models import Job, JobSeekerProfile

def compute_match_score(job, seeker):
    score = 0

    # ----- Skill Matching -----
    job_required = set(job.required_skills.values_list("id", flat=True))
    job_nice = set(job.nice_to_have_skills.values_list("id", flat=True))
    seeker_skills = set(seeker.skills.values_list("id", flat=True))

    required_overlap = len(job_required & seeker_skills)
    nice_overlap = len(job_nice & seeker_skills)

    score += required_overlap * 10     # required skills carry heavy weight
    score += nice_overlap * 3          # nice-to-have are lighter

    # ----- Location Matching -----
    if seeker.location and job.location:
        if seeker.location.lower() == job.location.lower():
            score += 5
        elif job.work_type == Job.WorkType.REMOTE:
            score += 2

    # ----- Keyword Matching Between Job Title & Seeker Summary -----
    if seeker.summary and job.title:
        title_words = job.title.lower().split()
        summary_text = seeker.summary.lower()
        matched_keywords = sum(1 for w in title_words if w in summary_text)
        score += matched_keywords * 1

    return score


def get_recommended_jobseekers(job):
    seekers = JobSeekerProfile.objects.prefetch_related("skills").all()

    scored = []

    for seeker in seekers:
        score = compute_match_score(job, seeker)
        if score > 0:
            scored.append((score, seeker))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [seeker for score, seeker in scored]
