import os
import shutil
import re
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Post
from .forms import PostForm, TextSubmissionForm
from django.http import HttpResponseForbidden
from backend.sent_bayes import SentimentAnalyzer
from django.urls import reverse
from time import sleep
from threading import Thread, Lock
from queue import Queue
from django.db import transaction

lock = Lock()

@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST' and 'delete_post' in request.POST:
        post.delete()
        return redirect('blog-home')  # Redirect to the list of posts after deletion
    return render(request, 'blog/post_detail.html', {'post': post})

@login_required
def post_create_view(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('post-detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form})


@login_required
def post_update_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        return HttpResponseForbidden()
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('post-detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_form.html', {'form': form})


@login_required
def post_delete_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        return HttpResponseForbidden()
    if request.method == 'POST':
        post.delete()
        return redirect('blog-home')
    return render(request, 'blog/post_confirm_delete.html', {'post': post})


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
def post_list_view(request):
    posts = Post.objects.filter(author=request.user).order_by('-date_posted')
    if request.method == 'POST' and 'delete_post' in request.POST:
        post_id = request.POST.get('post_id')
        post = get_object_or_404(Post, id=post_id, author=request.user)
        post.delete()
        return redirect('blog-home')  # Redirect to the list of posts after deletion
    return render(request, 'blog/home.html', {'posts': posts})

@login_required
def generate_document_view(request):
    if request.method == 'POST':
        database.ativar_summarize()
        document_result = database.tex_generator()
        return render(request, 'blog/generate_document.html', {'result': document_result})
    return render(request, 'blog/generate_document.html')

@login_required
def post_detail_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST' and 'delete_post' in request.POST:
        post.delete()
        return redirect('blog-home')  # Redirect to the list of posts after deletion
    return render(request, 'blog/post_detail.html', {'post': post})

def is_valid_html(content):
    # Verificar se a primeira linha do conteúdo contém uma tag HTML básica como <p>, <div>, <h1>, etc.
    return bool(re.search(r'<(p|div|h1|h2|h3|h4|h5|h6|span|a|img|ul|ol|li|table|tr|td|th|strong|em|br|hr|blockquote)[^>]*>', content, re.IGNORECASE))

@login_required
@transaction.atomic
def create_post_from_text(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data['content']
            text = text.replace('\\r\\n', '\\n')  # Normaliza quebras de linha
            analyzer = SentimentAnalyzer()

            def process_text(queue, text):
                result_html, images = analyzer.execute_analysis_text(text)
                queue.put((result_html, images))

            # Usar thread para a análise de texto
            queue = Queue()
            thread = Thread(target=process_text, args=(queue, text))
            thread.start()
            thread.join()

            result_html, images = queue.get()

            with lock:
                # Salvar o post apenas se o HTML for válido
                if is_valid_html(result_html):
                    post = Post(
                        title=form.cleaned_data['title'],
                        content=result_html,
                        author=request.user,
                        date_posted=timezone.now()
                    )
                    post.save()
                    for image_path in images:
                        post.images.create(image=image_path)
                    return redirect('post-detail', pk=post.pk)
                else:
                    # Lidar com falha na análise de texto
                    return render(request, 'blog/post_form.html', {'form': form, 'error': 'Erro ao processar o texto. Tente novamente.'})
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form})

