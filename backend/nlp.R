#!/usr/bin/env Rscript
args = commandArgs(trailingOnly=TRUE)

library('textshaping')
library('ragg')
library('tidyverse')
library('tm')
library('SnowballC')
library('wordcloud')
library('RColorBrewer')
library('ggplot2')
library('magrittr')
library('quanteda')
library('rainette')
library('syuzhet')

text <- readLines(args[1])
TextDoc <- Corpus(VectorSource(text))

toSpace <- content_transformer(function (x , pattern ) gsub(pattern, " ", x))
TextDoc <- tm_map(TextDoc, toSpace, "/")
TextDoc <- tm_map(TextDoc, toSpace, "@")
TextDoc <- tm_map(TextDoc, toSpace, "\\|")
TextDoc <- tm_map(TextDoc, content_transformer(tolower))
TextDoc <- tm_map(TextDoc, removeNumbers)
TextDoc <- tm_map(TextDoc, removeWords, stopwords(args[2]))
TextDoc <- tm_map(TextDoc, removePunctuation)
TextDoc <- tm_map(TextDoc, stripWhitespace)
TextDoc <- tm_map(TextDoc, stemDocument)

TextDoc_dtm <- TermDocumentMatrix(TextDoc)
dtm_m <- as.matrix(TextDoc_dtm)
dtm_v <- sort(rowSums(dtm_m),decreasing=TRUE)
dtm_d <- data.frame(word = names(dtm_v),freq=dtm_v)

d <- get_nrc_sentiment(text)
td <- data.frame(t(d))
td_new <- data.frame(rowSums(td[2:ncol(td)]))
names(td_new)[1] <- "count"
td_new <- cbind("sentiment" = rownames(td_new), td_new)
rownames(td_new) <- NULL
td_new2 <- td_new[1:8,]

plotname_wf <- function (name) {
    plotname_word_freq <- paste(gsub('.{0,4}$', '', name), "_word_freq.jpeg", sep= "")
    jpeg(file = plotname_word_freq)
    barplot(dtm_d[1:as.numeric(args[3]),]$freq, las = 2, names.arg = dtm_d[1:as.numeric(args[3]),]$word,
            col = "lightgreen", main = paste("Top", as.numeric(args[3]), "most frequent words", sep = " "),
            ylab = "Word frequencies")
    dev.off()

    path_file_name <- paste('media/image/plots/barplots/', plotname_word_freq, sep="")
    file.copy(from = plotname_word_freq,
              to = path_file_name)
    file.remove(plotname_word_freq)
}
plotname_wf(args[1])

plotname_wc <- function (name) {
    plotname_word_cloud <- paste(gsub('.{0,4}$', '', name), "_word_cloud.jpeg", sep="")
    jpeg(file = plotname_word_cloud)
    wordcloud(words = dtm_d$word, freq = dtm_d$freq, min.freq = args[4],
          max.words = 100, random.order = FALSE, rot.per = 0.40,
          colors = brewer.pal(8, "Dark2"))
    dev.off()

    path_file_name <- paste('media/image/plots/wordclouds/', plotname_word_cloud, sep="")
    file.copy(from = plotname_word_cloud,
              to = path_file_name)
    file.remove(plotname_word_cloud)
}
plotname_wc(args[1])

sentiments_1 <- function(name) {
    plotname_sents_1 <- paste(gsub('.{0,4}$', '', name), "_sents_1.jpeg", sep = "")
    path_file_name <- paste('media/image/plots/sents_1/', plotname_sents_1, sep = "")
    plot <- qplot(sentiment, data = td_new2, weight = count, geom = "bar", fill = sentiment, ylab = "count") + ggtitle("Survey sentiments")
    ggsave(filename=path_file_name, plot = plot)
}
sentiments_1(args[1])

reinert <- function(TextDoc, name){
    corpus <- split_segments(TextDoc, segment_size = as.numeric(args[5]))
    tok <- tokens(corpus, remove_punct = TRUE)
    tok <- tokens_remove(tok, stopwords(args[6]))
    dtm <- dfm(tok, tolower = TRUE)
    dtm <- dfm_trim(dtm, min_docfreq = as.numeric(args[7]))
    res <- rainette(dtm, k = as.numeric(args[8]), min_segment_size = as.numeric(args[9]))

    reinert_name <- paste(gsub('.{0,4}$', '', name), "_reinert.png", sep = "")
    path_file_name <- paste('media/image/plots/reinerts/', reinert_name, sep = "")
    g <- rainette_plot(res, dtm, k = as.numeric(args[8]))
    ggsave(reinert_name, g)
    
    file.copy(from = reinert_name,
              to = path_file_name)
    file.remove(reinert_name)  
    }
reinert(TextDoc, args[1])
