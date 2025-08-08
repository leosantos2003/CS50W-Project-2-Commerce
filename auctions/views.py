from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from django.db.models import Max

from django.contrib.auth.decorators import login_required
from .models import User, Listing, Category

from django.shortcuts import get_object_or_404


def index(request):
    # Filtra o banco de dados para pegar apenas os anúncios onde is_active = True
    # Annotate serve para criar um campo temporário 'max_bid para cada anúncio
    # Este campo conterá o valor máximo (Max) do campo 'amount' dos lances ('bids')   
    active_listings = Listing.objects.filter(is_active=True).annotate(
        max_bid=Max('bids__amount')
    )

    # Envia a lista de anúncios para o template através do contexto
    return render(request, "auctions/index.html", {
        "listings": active_listings
    })


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
        image_url = request.POST.get("image_url") # .get() é bom para campos opcionais também

        # Validação básica
        if not title or not description or not starting_bid:
            return render(request, "auctions/create.html", {
                "message": "Title, description, and starting bid are required.",
                "categories": Category.objects.all()
            })
        
        # Usar .get() é mais seguro, pois retorna None se a chave não existir, em vez de quebrar.
        category_id = request.POST.get("category")

        # Obter o objeto Category
        # Só busca a categoria se um ID foi realmente enviado.
        category = Category.objects.get(pk=category_id) if category_id else None

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
            "categories": Category.objects.all()
        })
    
def listing_page(request, listing_id):
    # Busca o anúncio pelo ID. Se não encontrar, retorna um erro 404.
    listing = get_object_or_404(Listing, pk=listing_id)

    # Lógica para determinar o preço atual (maior lance ou lance inicial)
    highest_bid = listing.bids.order_by('-amount').first()
    current_price = highest_bid.amount if highest_bid else listing.starting_bid

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "current_price": current_price
    })