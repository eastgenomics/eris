FROM nginx:1.23

RUN apt-get -y update
RUN apt-get -y install vim

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d