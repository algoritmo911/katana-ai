package utils

import (
	"fmt"
	"os/exec"
)

const (
	telepresenceInstallInstructions = `
'telepresence' is not installed or not found in your PATH.
Please install it to continue.

Instructions:

macOS (using Homebrew):
  brew install datawire/blackbird/telepresence

Linux:
  sudo curl -fL https://app.getambassador.io/download/tel2/linux/amd64/latest/telepresence -o /usr/local/bin/telepresence
  sudo chmod a+x /usr/local/bin/telepresence

Windows:
  Please refer to the official documentation: https://www.telepresence.io/docs/latest/install
`
	kubectlConnectionInstructions = `
Could not connect to a Kubernetes cluster.
Please ensure 'kubectl' is configured correctly and you have a valid kubeconfig file.

You can test your connection with:
  kubectl cluster-info
`
)

// CheckTelepresenceInstalled verifies that the telepresence binary is installed and in the PATH.
func CheckTelepresenceInstalled() error {
	_, err := exec.LookPath("telepresence")
	if err != nil {
		return fmt.Errorf(telepresenceInstallInstructions)
	}
	return nil
}

// CheckKubectlConnection verifies that kubectl is configured and can connect to a cluster.
func CheckKubectlConnection() error {
	cmd := exec.Command("kubectl", "cluster-info")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf(kubectlConnectionInstructions)
	}
	return nil
}
