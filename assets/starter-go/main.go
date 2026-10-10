// Minimal Windows exe skeleton.
// Build: python scripts/build_exe.py --src . --out dist/myapp.exe
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

var version = "1.0.0"

func main() {
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *showVersion {
		fmt.Printf("myapp %s (%s/%s)\n", version, runtime.GOOS, runtime.GOARCH)
		return
	}

	fmt.Println("myapp is running")
	fmt.Println("config dir:", configDir())

	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

func run() error {
	// Your logic here.
	return nil
}

// configDir returns %APPDATA%\MyApp - the safe place to write user data.
func configDir() string {
	base, err := os.UserConfigDir()
	if err != nil {
		return filepath.Join(os.TempDir(), "myapp")
	}
	dir := filepath.Join(base, "MyApp")
	os.MkdirAll(dir, 0755)
	return dir
}
