from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction

from accounts.models import User
from .models import JobSeekerProfile
from .forms import ProfileForm, EducationFormSet, ExperienceFormSet, LinkFormSet


@login_required
def my_profile(request):
    profile, _ = JobSeekerProfile.objects.get_or_create(user=request.user)
    ctx = {
        "profile": profile,
        "experiences_qs": profile.experiences.filter(show=True),
        "educations_qs": profile.educations.filter(show=True),
        "links_qs": profile.links.filter(show=True),
    }
    return render(request, "profiles/profile_detail.html", ctx)


def public_profile(request, username: str):
    user = get_object_or_404(User, username=username)
    if not hasattr(user, "profile"):
        return render(request, "profiles/no_profile.html", {"target": user})
    profile = user.profile
    ctx = {
        "profile": profile,
        "experiences_qs": profile.experiences.filter(show=True),
        "educations_qs": profile.educations.filter(show=True),
        "links_qs": profile.links.filter(show=True),
    }
    return render(request, "profiles/profile_detail.html", ctx)

@login_required
def edit_profile(request):
    profile, _ = JobSeekerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Bind with SAME prefixes used in the template
        pform = ProfileForm(request.POST, instance=profile)
        efs   = EducationFormSet(request.POST, instance=profile, prefix="edu")
        xfs   = ExperienceFormSet(request.POST, instance=profile, prefix="exp")
        lfs   = LinkFormSet(request.POST, instance=profile, prefix="lnk")

        if pform.is_valid() and efs.is_valid() and xfs.is_valid() and lfs.is_valid():
            with transaction.atomic():
                profile = pform.save()

                # Overwrite semantics: DB exactly matches form content
                def overwrite(fs, related_qs):
                    kept_existing_ids = set()
                    for form in fs.forms:
                        cd = getattr(form, "cleaned_data", None)
                        if not cd:
                            continue
                        if cd.get("DELETE"):
                            continue
                        inst = cd.get("id")
                        if inst:
                            kept_existing_ids.add(inst.id)

                    existing_ids = set(related_qs.values_list("id", flat=True))
                    to_delete = existing_ids - kept_existing_ids
                    if to_delete:
                        related_qs.filter(id__in=to_delete).delete()

                    fs.save()  # apply updates, create new, and honor DELETE

                overwrite(efs, profile.educations.all())
                overwrite(xfs, profile.experiences.all())
                overwrite(lfs, profile.links.all())

            messages.success(request, "Your profile was updated.")
            return redirect("profiles:my_profile")
        else:
            # Top-of-page banner if any validation failed
            messages.error(request, "Please fix the errors below and try again.")
    else:
        pform = ProfileForm(instance=profile)
        efs   = EducationFormSet(instance=profile, prefix="edu")
        xfs   = ExperienceFormSet(instance=profile, prefix="exp")
        lfs   = LinkFormSet(instance=profile, prefix="lnk")

    ctx = {"pform": pform, "eformset": efs, "xformset": xfs, "lformset": lfs}
    return render(request, "profiles/profile_edit.html", ctx)
