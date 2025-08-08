from urllib import request
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from django.db.models import Max

from django.contrib.auth.decorators import login_required
from .models import User, Listing, Category, Bid, Comment

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
    
# Em auctions/views.py

def listing_page(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    is_on_watchlist = request.user.is_authenticated and request.user in listing.watchlist.all()
    comments = listing.comments.all().order_by('-created_at') # Pega os comentários

    if request.method == "POST":
        # Processa um novo lance
        if "submit_bid" in request.POST:
            try:
                bid_amount = float(request.POST["bid_amount"])
            except ValueError:
                return render(request, "auctions/listing.html", { "listing": listing, "is_on_watchlist": is_on_watchlist, "comments": comments, "error": "Invalid bid amount." })
            
            highest_bid = listing.bids.order_by('-amount').first()
            current_price = highest_bid.amount if highest_bid else listing.starting_bid

            if bid_amount < listing.starting_bid or bid_amount <= current_price:
                return render(request, "auctions/listing.html", { "listing": listing, "is_on_watchlist": is_on_watchlist, "comments": comments, "current_price": current_price, "error": "Your bid must be higher than the starting bid and the current price." })
            
            new_bid = Bid(amount=bid_amount, bidder=request.user, listing=listing)
            new_bid.save()
            return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))

        # Processa um novo comentário
        elif "submit_comment" in request.POST:
            comment_text = request.POST["comment_text"]
            if comment_text: # Garante que o comentário não está vazio
                new_comment = Comment(text=comment_text, author=request.user, listing=listing)
                new_comment.save()
            return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))

    # Lógica para exibir a página (GET)
    highest_bid = listing.bids.order_by('-amount').first()
    current_price = highest_bid.amount if highest_bid else listing.starting_bid
    
    return render(request, "auctions/listing.html", {
        "listing": listing,
        "is_on_watchlist": is_on_watchlist,
        "current_price": current_price,
        "comments": comments
    })

@login_required
def add_watchlist(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    listing.watchlist.add(request.user)
    return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))

@login_required
def remove_watchlist(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    listing.watchlist.remove(request.user)
    return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))

@login_required
def close_auction(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)

    # Verifica se o usuário logado é o criador do conteúdo
    if request.user == listing.creator:
        # Encontra o maior lance
        highest_bid = listing.bids.order_by('-amount').first()

        if highest_bid:
            # Define o vencedor
            listing.winner = highest_bid.bidder

        # Desativa o anúncio
        listing.is_active = False
        listing.save()

    return HttpResponseRedirect(reverse("listing_page", args=[listing_id]))
