from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from django.contrib.auth.decorators import login_required
from .models import User, Listing, Category


def index(request):
    return render(request, "auctions/index.html")


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

@login_required
def create_listing(request):
    if request.method == "POST":
        # Processar o formulário enviado
        title = request.POST["title"]
        description = request.POST["description"]
        starting_bid = request.POST["starting_bid"]
        image_url = request.POST["image_url"]
        category_id = request.POST["category"]

        # Validação básica
        if not title or not description or not starting_bid:
            return render(request, "auctions/create.html", {
                "message": "Title, description, and starting bid are required.",
                "categories": Category.objects.all()
            })
        
        # Obter o objeto Category
        category = Category.objects.get(pk=category_id)

        # Criar o novo anúncio no banco de dados
        new_listing = Listing(
            title=title,
            description=description,
            starting_bid=float(starting_bid),
            image_url=image_url,
            category=category,
            creator=request.user
        )
        new_listing.save()

        # Redirecionar para a página inicial
        return HttpResponseRedirect(reverse("index"))
    else:
        # Mostrar o formulário em branco
        return render(request, "auctions/create.html", {
            "catoegories": Category.objects.all()
        })