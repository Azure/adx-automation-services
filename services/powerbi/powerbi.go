package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"github.com/Azure/adx-automation-agent/common"
	"github.com/Azure/adx-automation-agent/kubeutils"
	"github.com/Azure/go-autorest/autorest"
	"github.com/Azure/go-autorest/autorest/adal"
	"github.com/Azure/go-autorest/autorest/azure"
)

type PowerBIService interface {
	Refresh(context.Context, string, int64) error
}

type powerBIService struct{}

const (
	emptyProductError = "'product' is not set"
	skipTemplate      = "secret does not have a `%s` key. Skipping Power BI refresh"
	groupKey          = "powerbi.group"
	datasetKey        = "powerbi.dataset"
	maxAttempts       = 20
	sleepTime         = time.Second * 30
)

// Refresh refreshes a PowerBI dataset.
// See https://powerbi.microsoft.com/en-us/blog/announcing-data-refresh-apis-in-the-power-bi-service/
func (powerBIService) Refresh(_ context.Context, product string, runID int64) error {
	common.LogInfo("starting with PowerBI refresh")
	// get parameters
	if product == "" {
		return errors.New(emptyProductError)
	}
	secret, err := kubeutils.TryCreateKubeClientset().
		CoreV1().
		Secrets(common.GetCurrentNamespace("a01-prod")).
		Get(product, metav1.GetOptions{})
	if err != nil {
		return fmt.Errorf("failed to get the kubernetes secret: %v", err)
	}

	group, ok := secret.Data[groupKey]
	if !ok {
		return fmt.Errorf(skipTemplate, groupKey)
	}
	dataset, ok := secret.Data[datasetKey]
	if !ok {
		return fmt.Errorf(skipTemplate, datasetKey)
	}
	common.LogInfo(fmt.Sprintf("runID: %d | product: %s | group: %s | dataset: %s",
		runID,
		product,
		string(group),
		string(dataset)))

	// get client and authorizer
	client := autorest.NewClientWithUserAgent("")
	authorizer, err := getAuth()
	if err != nil {
		return fmt.Errorf("failed to get authorizer: %v", err)
	}
	client.Authorizer = authorizer

	uri := fmt.Sprintf("https://api.powerbi.com/v1.0/myorg/groups/%s/datasets/%s/refreshes", string(group), string(dataset))

	err = refresh(client, uri)
	if err != nil {
		return fmt.Errorf("failed sending refresh request: %s", err)
	}

	err = poll(client, uri)
	if err != nil {
		return fmt.Errorf("failed polling for refresh completion: %s", err)
	}

	return nil
}

func getAuth() (a autorest.Authorizer, err error) {
	clientID := os.Getenv("A01_POWERBI_CLIENT_ID")
	username := os.Getenv("A01_POWERBI_USERNAME")
	password := os.Getenv("A01_POWERBI_PASSWORD")

	endpoint, err := url.Parse("https://login.windows.net/common/oauth2/token")
	config := adal.OAuthConfig{
		TokenEndpoint: *endpoint,
	}
	if err != nil {
		return a, fmt.Errorf("failed to parse token endpoint: %v", err)
	}
	spt, err := adal.NewServicePrincipalTokenFromUsernamePassword(
		config,
		clientID,
		username,
		password,
		"https://analysis.windows.net/powerbi/api")
	if err != nil {
		return a, fmt.Errorf("failed to create a new service principal token: %v", err)
	}
	return autorest.NewBearerAuthorizer(spt), nil
}

func refresh(client autorest.Client, uri string) error {
	req, err := http.NewRequest(http.MethodPost, uri, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}

	common.LogInfo("sending refresh request...")

	resp, err := autorest.SendWithSender(client, req,
		autorest.DoRetryForStatusCodes(client.RetryAttempts, client.RetryDuration, autorest.StatusCodesForRetry...))
	if err != nil {
		return fmt.Errorf("failed to send refresh request: %v", err)
	}

	err = autorest.Respond(
		resp,
		client.ByInspecting(),
		azure.WithErrorUnlessStatusCode(http.StatusOK, http.StatusAccepted),
		autorest.ByClosing())
	if err != nil {
		return fmt.Errorf("failed to respond to PowerBI refresh response: %v", err)
	}
	common.LogInfo("refresh request successful")
	return nil
}

type RefreshHistory struct {
	Context   string       `json:"@odata.context"`
	Refreshes []PBIRefresh `json:"value"`
}

type PBIRefresh struct {
	ID          int64  `json:"id"`
	RefreshType string `json:"refreshType"`
	StartTime   string `json:"startTime"`
	EndTime     string `json:"endTime"`
	Status      string `json:"status"`
}

func (pbi PBIRefresh) String() string {
	return fmt.Sprintf("Refresh ID: %d\nType: %s\nStart: %s\nEnd: %s\nStatus: %s\n",
		pbi.ID,
		pbi.RefreshType,
		pbi.StartTime,
		pbi.EndTime,
		pbi.Status)
}

func poll(client autorest.Client, uri string) error {
	common.LogInfo("starting to poll for completion")
	status := ""
	count := 1

	for status != "Completed" && count <= maxAttempts {
		common.LogInfo(fmt.Sprintf("polling for completion, attempt %d", count))
		common.LogInfo("sleeping...")
		time.Sleep(sleepTime)

		req, err := http.NewRequest(http.MethodGet, uri, nil)
		if err != nil {
			return fmt.Errorf("failed to create request: %v", err)
		}

		common.LogInfo("sending refresh request...")

		resp, err := autorest.SendWithSender(client, req,
			autorest.DoRetryForStatusCodes(client.RetryAttempts, client.RetryDuration, autorest.StatusCodesForRetry...))
		if err != nil {
			return fmt.Errorf("failed to send refresh history request: %v", err)
		}

		var result RefreshHistory

		err = autorest.Respond(
			resp,
			client.ByInspecting(),
			azure.WithErrorUnlessStatusCode(http.StatusOK),
			autorest.ByUnmarshallingJSON(&result),
			autorest.ByClosing())
		if err != nil {
			return fmt.Errorf("failed to respond to PowerBI refresh history response: %v", err)
		}
		common.LogInfo("refresh history request successful")

		status = result.Refreshes[0].Status
		common.LogInfo(result.Refreshes[0].String())
		count++
	}
	if status != "Completed" {
		return fmt.Errorf("refresh not completed. Status is %s", status)
	}

	common.LogInfo("finished polling for completion")
	return nil
}
