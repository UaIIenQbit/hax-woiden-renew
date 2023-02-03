FROM python:bullseye

WORKDIR /app
ENV PATH="/app:${PATH}"
COPY . .

RUN apt update \ 
	&& apt install ffmpeg -y \
	&& apt clean \
	&& rm -rf /var/lib/apt/lists/* \
	&&  pip install --no-cache-dir -r requirements.txt \ 
	&& python -m playwright install \
 	&& playwright install-deps

ENTRYPOINT ["python3","main.py"]
