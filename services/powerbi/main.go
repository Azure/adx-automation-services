package main

import (
	"log"
	"net/http"

	"github.com/Azure/adx-automation-agent/common"
	httptransport "github.com/go-kit/kit/transport/http"
)

func main() {
	common.LogInfo("Initiating PowerBI refresh microservice")
	svc := powerBIService{}

	refreshHandler := httptransport.NewServer(
		makeRefreshEndpoint(svc),
		decodeRefreshRequest,
		encodeResponse,
	)

	http.Handle("/report", refreshHandler)
	log.Fatal(http.ListenAndServe(":80", nil))
}
