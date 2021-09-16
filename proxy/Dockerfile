FROM nginx:1.21.3-alpine
COPY entrypoint.sh default.conf.template /
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]