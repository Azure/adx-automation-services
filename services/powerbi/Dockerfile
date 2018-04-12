FROM golang:1.10-alpine

COPY . /go/src/github.com/Azure/adx-automation-services/services/powerbi

RUN apk add --no-cache git bash && \
    go get github.com/golang/dep/cmd/dep

WORKDIR /go/src/github.com/Azure/adx-automation-services/services/powerbi
RUN dep ensure && \
    go install

EXPOSE 80

CMD powerbi