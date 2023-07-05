from django.shortcuts import render
from django.core.paginator import Paginator

from requests_app.models import ClinicalIndication


def index(request):
    all_ci = ClinicalIndication.objects.all()
    paginator = Paginator(
        all_ci,
        per_page=10,
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "web/index.html", {"page_obj": page_obj})
