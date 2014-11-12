from django.shortcuts import render

def index(request):
    context = {"page": {"title": "Home"}}
    return render(request, 'index.html', context)

def data_access(request):
    context = {"page": {"title": "Data Access"}}
    return render(request, 'data.html', context)

def science(request):
    context = {"page": {"title": "Science"}}
    return render(request, 'science.html', context)

def contact(request):
    context = {"page": {"title": "Contact"}}
    return render(request, 'contact.html', context)
