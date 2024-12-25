# Use a imagem base do R
FROM r-base:latest

# Instale pacotes R necessários
RUN Rscript -e "install.packages(c('tidyverse', 'syuzhet', 'textshaping', 'ragg', 'tm', 'SnowballC', 'wordcloud', 'RColorBrewer', 'syuzhet', 'ggplot2', 'magrittr', 'quanteda', 'rainette'), repos='http://cran.us.r-project.org')"

# Change the default entrypoint for R to avoid fatal error
CMD ["R", "--no-save"]