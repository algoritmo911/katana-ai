package cmd

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/algoritmo911/katana-ai/pkg/utils"
	"github.com/spf13/cobra"
)

var (
	serviceName string
	localPort   int
)

// connectCmd represents the connect command
var connectCmd = &cobra.Command{
	Use:   "connect <environment>",
	Short: "Connects to a remote Kubernetes environment and intercepts a service.",
	Long: `Establishes a connection to a specified Kubernetes environment using Telepresence,
and then intercepts traffic from a service, redirecting it to a local process.

This allows you to debug your local service as if it were running inside the cluster.`,
	Args: cobra.ExactArgs(1), // Ensures exactly one argument (the environment) is passed.
	Run: func(cmd *cobra.Command, args []string) {
		// 1. Run prerequisite checks
		if err := utils.CheckTelepresenceInstalled(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		if err := utils.CheckKubectlConnection(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}

		environment := args[0]
		fmt.Printf("Attempting to connect to environment: %s\n", environment)

		// 2. Execute telepresence connect
		fmt.Println("--> Running 'telepresence connect'...")
		tpConnectCmd := exec.Command("telepresence", "connect")
		tpConnectCmd.Stdout = os.Stdout
		tpConnectCmd.Stderr = os.Stderr
		if err := tpConnectCmd.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "Error during 'telepresence connect': %v\n", err)
			os.Exit(1)
		}
		fmt.Println("--> Connection established.")

		// 3. Execute telepresence intercept
		fmt.Printf("--> Intercepting service '%s' on local port '%d'...\n", serviceName, localPort)
		tpInterceptCmd := exec.Command("telepresence", "intercept", serviceName, "--port", fmt.Sprintf("%d", localPort))
		tpInterceptCmd.Stdout = os.Stdout
		tpInterceptCmd.Stderr = os.Stderr
		tpInterceptCmd.Stdin = os.Stdin // For interactive session

		if err := tpInterceptCmd.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "Error during 'telepresence intercept': %v\n", err)
			os.Exit(1)
		}

		fmt.Println("\n--> Intercept successful! Telepresence may have created a .env file in this directory.")
		fmt.Println("--> Start your local service using this file to inherit the environment variables from the remote pod.")
		fmt.Println("--> Example: docker run --rm -it --env-file=.env <your-image>")
	},
}

func init() {
	rootCmd.AddCommand(connectCmd)
	connectCmd.Flags().StringVarP(&serviceName, "service", "s", "", "The name of the service to intercept")
	connectCmd.Flags().IntVarP(&localPort, "port", "p", 0, "The local port your service is running on")
	connectCmd.MarkFlagRequired("service")
	connectCmd.MarkFlagRequired("port")
}
