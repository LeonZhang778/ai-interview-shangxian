FROM nginx:alpine

# 删除默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制 Nginx 配置
COPY default.conf /etc/nginx/conf.d/default.conf

# 前端构建产物会在 docker-compose 中通过 volume 映射
# 也可以在这里 COPY, 但 volume 更方便更新
