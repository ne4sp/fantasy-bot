FROM python:3.13-slim
# set work directory
WORKDIR /usr/src/app/
# copy project
COPY . /usr/src/app/
# install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# run app
CMD ["python", "main.py"]