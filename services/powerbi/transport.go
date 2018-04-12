package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/Azure/adx-automation-agent/common"
	"github.com/go-kit/kit/endpoint"
)

func makeRefreshEndpoint(svc PowerBIService) endpoint.Endpoint {
	return func(ctx context.Context, request interface{}) (interface{}, error) {
		req := request.(refreshRequest)
		err := svc.Refresh(ctx, req.Product, req.RunID)
		if err != nil {
			return refreshResponse{
				Err: err.Error(),
			}, nil
		}
		return refreshResponse{}, nil
	}
}

type refreshRequest struct {
	Product string `json:"product"`
	RunID   int64  `json:"runID"`
}

type refreshResponse struct {
	Err string `json:"err,omitempty"`
}

func decodeRefreshRequest(_ context.Context, r *http.Request) (interface{}, error) {
	var req refreshRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		return nil, err
	}
	return req, nil
}

func encodeResponse(_ context.Context, w http.ResponseWriter, response interface{}) error {
	resp := response.(refreshResponse)
	Error := resp.Err
	status := http.StatusOK
	if Error != "" {
		common.LogError(fmt.Sprintf("refresh failed: %s", Error))
		switch Error {
		case emptyProductError:
			status = http.StatusBadRequest
			break
		default:
			status = http.StatusInternalServerError
			break
		}
	}
	common.LogInfo(fmt.Sprintf("returning %d status code", status))
	w.WriteHeader(status)
	return json.NewEncoder(w).Encode(response)
}
