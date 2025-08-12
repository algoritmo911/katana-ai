package cmd

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/spf13/cobra"
)

// disconnectCmd represents the disconnect command
var disconnectCmd = &cobra.Command{
	Use:   "disconnect <service-name>",
	Short: "Removes an intercept and disconnects from the environment.",
	Long: `Removes an active Telepresence intercept for a specific service and then
terminates the Telepresence connection to the cluster.`,
	Args: cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		serviceName := args[0]

		// 1. Leave the intercept
		fmt.Printf("--> Leaving intercept for service '%s'...\n", serviceName)
		tpLeaveCmd := exec.Command("telepresence", "leave", serviceName)
		tpLeaveCmd.Stdout = os.Stdout
		tpLeaveCmd.Stderr = os.Stderr
		if err := tpLeaveCmd.Run(); err != nil {
			// Telepresence already prints a good error message, so we just exit.
			// Example: "intercept <service-name> not found"
			os.Exit(1)
		}
		fmt.Println("--> Intercept successfully removed.")

		// 2. Quit Telepresence
		fmt.Println("--> Shutting down Telepresence connection...")
		tpQuitCmd := exec.Command("telepresence", "quit")
		tpQuitCmd.Stdout = os.Stdout
		tpQuitCmd.Stderr = os.Stderr
		if err := tpQuitCmd.Run(); err != nil {
			fmt.Fprintf(os.Stderr, "Error during 'telepresence quit': %v\n", err)
			os.Exit(1)
		}
		fmt.Println("--> Disconnected successfully.")
	},
}

func init() {
	rootCmd.AddCommand(disconnectCmd)
}
