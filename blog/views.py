import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from main import Main  # Importando o módulo main do backend

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from .models import Post

# Inicialize a classe Main
database = Main()

class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'
    context_object_name = 'posts'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['new_post_url'] = 'choose_database'  # URL para iniciar um novo post
        return context

class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content']
    template_name = 'blog/post_form.html'

@login_required
def choose_database_view(request):
    if request.method == 'POST':
        if 'select_db' in request.POST:
            database_name = request.POST.get('database_name')
            database.atualizar_banco(database_name)
            return redirect('main_menu')
        elif 'create_db' in request.POST:
            database_name = request.POST.get('new_database_name')
            database.atualizar_banco(database_name)
            return redirect('main_menu')
    existing_databases = ['db1', 'db2']  # Substitua por lógica para listar os bancos existentes
    return render(request, 'blog/choose_database.html', {'databases': existing_databases})

@login_required
def main_menu_view(request):
    if request.method == 'POST':
        option = request.POST.get('option')
        if option == '1':
            return redirect('insert_links')
        elif option == '2':
            return redirect('remove_data')
        elif option == '3':
            return redirect('update_data')
        elif option == '4':
            return redirect('generate_document')
        elif option == '5':
            return redirect('logout')
    return render(request, 'blog/main_menu.html')

@login_required
def insert_links_view(request):
    if request.method == 'POST':
        link = request.POST.get('link')
        database.registrar_link(link)
    return render(request, 'blog/insert_links.html')

@login_required
def remove_data_view(request):
    if request.method == 'POST':
        table = request.POST.get('table')
        condition = request.POST.get('condition')
        database.conectar()
        database.cursor.execute(f"DELETE FROM {table} WHERE {condition}")
        database.conexao.commit()
        database.desconectar()
    return render(request, 'blog/remove_data.html')

@login_required
def update_data_view(request):
    if request.method == 'POST':
        table = request.POST.get('table')
        column = request.POST.get('column')
        new_value = request.POST.get('new_value')
        condition = request.POST.get('condition')
        database.conectar()
        query = f"UPDATE {table} SET {column}='{new_value}' WHERE {condition}"
        database.cursor.execute(query)
        database.conexao.commit()
        database.desconectar()
    return render(request, 'blog/update_data.html')

@login_required
def generate_document_view(request):
    if request.method == 'POST':
        database.ativar_summarize()
        document_result = database.tex_generator()
        return render(request, 'blog/generate_document.html', {'result': document_result})
    return render(request, 'blog/generate_document.html')
