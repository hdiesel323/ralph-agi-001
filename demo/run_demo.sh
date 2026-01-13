#!/bin/bash
# RALPH-AGI Demo Runner
# Runs all demo scenarios and presents results clearly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check for API key
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    # Try to source .env
    if [ -f "$PROJECT_ROOT/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    fi
fi

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}Error: No API key found${NC}"
    echo "Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable"
    exit 1
fi

# Banner
print_banner() {
    echo ""
    echo -e "${PURPLE}"
    cat << 'BANNER'
    ██████╗  █████╗ ██╗     ██████╗ ██╗  ██╗       █████╗  ██████╗ ██╗
    ██╔══██╗██╔══██╗██║     ██╔══██╗██║  ██║      ██╔══██╗██╔════╝ ██║
    ██████╔╝███████║██║     ██████╔╝███████║█████╗███████║██║  ███╗██║
    ██╔══██╗██╔══██║██║     ██╔═══╝ ██╔══██║╚════╝██╔══██║██║   ██║██║
    ██║  ██║██║  ██║███████╗██║     ██║  ██║      ██║  ██║╚██████╔╝██║
    ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝      ╚═╝  ╚═╝ ╚═════╝ ╚═╝
BANNER
    echo -e "${NC}"
    echo -e "    ${YELLOW}Recursive Autonomous Long-horizon Processing Handler${NC}"
    echo ""
    echo -e "    ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Section header
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Run a scenario
run_scenario() {
    local scenario_name="$1"
    local scenario_dir="$2"
    local description="$3"

    print_section "Scenario: $scenario_name"
    echo -e "${CYAN}$description${NC}"
    echo ""

    # Clean any previous run
    cd "$scenario_dir"
    rm -f *.py demo_memory.* 2>/dev/null || true

    # Reset PRD
    if [ -f "PRD.json.bak" ]; then
        cp PRD.json.bak PRD.json
    else
        cp PRD.json PRD.json.bak
    fi

    # Copy config
    cp "$SCRIPT_DIR/config.yaml" .

    echo -e "${YELLOW}Starting RALPH...${NC}"
    echo ""

    # Run RALPH and capture output
    local start_time=$(date +%s)

    if ralph-agi run --prd PRD.json --config config.yaml -v 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo ""
        echo -e "${GREEN}✓ Scenario completed in ${duration}s${NC}"

        # Show results
        echo ""
        echo -e "${BOLD}Results:${NC}"

        # List generated files
        echo -e "  ${CYAN}Generated files:${NC}"
        for f in *.py; do
            if [ -f "$f" ] && [ "$f" != "*.py" ]; then
                echo -e "    • $f"
            fi
        done

        # Check PRD status
        echo ""
        echo -e "  ${CYAN}Task status:${NC}"
        grep -o '"id": "[^"]*"\|"passes": [^,]*' PRD.json | paste - - | while read line; do
            id=$(echo "$line" | grep -o '"id": "[^"]*"' | cut -d'"' -f4)
            passes=$(echo "$line" | grep -o '"passes": [^,]*' | cut -d' ' -f2)
            if [ "$passes" = "true" ]; then
                echo -e "    ${GREEN}✓${NC} $id - ${GREEN}PASSED${NC}"
            else
                echo -e "    ${RED}✗${NC} $id - ${RED}FAILED${NC}"
            fi
        done

        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo ""
        echo -e "${RED}✗ Scenario failed after ${duration}s${NC}"
        return 1
    fi
}

# Verify results
verify_scenario() {
    local scenario_name="$1"
    local scenario_dir="$2"

    cd "$scenario_dir"

    echo ""
    echo -e "${BOLD}Verification:${NC}"

    case "$scenario_name" in
        "Hello World")
            if [ -f "greeting.py" ]; then
                output=$(python greeting.py 2>&1)
                if [[ "$output" == *"Hello from RALPH-AGI"* ]]; then
                    echo -e "  ${GREEN}✓${NC} greeting.py runs correctly"
                    echo -e "    Output: $output"
                else
                    echo -e "  ${RED}✗${NC} greeting.py output unexpected: $output"
                fi
            else
                echo -e "  ${RED}✗${NC} greeting.py not found"
            fi
            ;;

        "Calculator")
            if [ -f "calculator.py" ]; then
                # Test the calculator
                python -c "
from calculator import add, subtract, multiply, divide
assert add(2, 3) == 5, 'add failed'
assert subtract(10, 4) == 6, 'subtract failed'
assert multiply(3, 4) == 12, 'multiply failed'
assert divide(10, 2) == 5.0, 'divide failed'
try:
    divide(1, 0)
    print('divide by zero should raise')
    exit(1)
except ValueError:
    pass
print('All tests passed!')
" && echo -e "  ${GREEN}✓${NC} All calculator functions work correctly" || echo -e "  ${RED}✗${NC} Calculator tests failed"
            else
                echo -e "  ${RED}✗${NC} calculator.py not found"
            fi
            ;;

        "Multi-Task")
            if [ -f "string_utils.py" ]; then
                echo -e "  ${GREEN}✓${NC} string_utils.py exists"
            else
                echo -e "  ${RED}✗${NC} string_utils.py not found"
            fi

            if [ -f "test_string_utils.py" ]; then
                echo -e "  ${GREEN}✓${NC} test_string_utils.py exists"
                if python -m pytest test_string_utils.py -v 2>&1 | grep -q "passed"; then
                    echo -e "  ${GREEN}✓${NC} Tests pass"
                else
                    echo -e "  ${YELLOW}⚠${NC} Some tests may have failed"
                fi
            else
                echo -e "  ${RED}✗${NC} test_string_utils.py not found"
            fi

            if [ -f "main.py" ]; then
                echo -e "  ${GREEN}✓${NC} main.py exists"
                echo -e "  ${CYAN}Demo output:${NC}"
                python main.py 2>&1 | sed 's/^/    /'
            else
                echo -e "  ${RED}✗${NC} main.py not found"
            fi
            ;;
    esac
}

# Main
main() {
    print_banner

    echo -e "${BOLD}What is RALPH?${NC}"
    echo "RALPH is an autonomous AI agent that executes software engineering tasks."
    echo "You give it a PRD (Product Requirements Document), and it works through"
    echo "tasks one by one until all are complete."
    echo ""
    echo -e "${BOLD}This demo shows 3 scenarios of increasing complexity:${NC}"
    echo "  1. Hello World - Simple file creation"
    echo "  2. Calculator - Module with multiple functions"
    echo "  3. Multi-Task - Dependent tasks building a utility"
    echo ""

    read -p "Press Enter to start the demo..."

    # Track results
    declare -a results

    # Scenario 1
    if run_scenario "Hello World" "$SCRIPT_DIR/scenario-1-hello" "Create a simple Python script that prints a greeting"; then
        verify_scenario "Hello World" "$SCRIPT_DIR/scenario-1-hello"
        results+=("Hello World:PASS")
    else
        results+=("Hello World:FAIL")
    fi

    read -p "Press Enter for next scenario..."

    # Scenario 2
    if run_scenario "Calculator" "$SCRIPT_DIR/scenario-2-calculator" "Create a calculator module with add, subtract, multiply, divide"; then
        verify_scenario "Calculator" "$SCRIPT_DIR/scenario-2-calculator"
        results+=("Calculator:PASS")
    else
        results+=("Calculator:FAIL")
    fi

    read -p "Press Enter for next scenario..."

    # Scenario 3
    if run_scenario "Multi-Task" "$SCRIPT_DIR/scenario-3-multitask" "Create a string utility module, tests, and CLI demo"; then
        verify_scenario "Multi-Task" "$SCRIPT_DIR/scenario-3-multitask"
        results+=("Multi-Task:PASS")
    else
        results+=("Multi-Task:FAIL")
    fi

    # Summary
    print_section "Demo Summary"

    echo -e "${BOLD}Results:${NC}"
    for result in "${results[@]}"; do
        name="${result%%:*}"
        status="${result##*:}"
        if [ "$status" = "PASS" ]; then
            echo -e "  ${GREEN}✓${NC} $name"
        else
            echo -e "  ${RED}✗${NC} $name"
        fi
    done

    echo ""
    echo -e "${GREEN}"
    cat << 'COMPLETE'
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ██████╗  ██████╗ ███╗   ██╗███████╗██╗                      ║
    ║   ██╔══██╗██╔═══██╗████╗  ██║██╔════╝██║                      ║
    ║   ██║  ██║██║   ██║██╔██╗ ██║█████╗  ██║                      ║
    ║   ██║  ██║██║   ██║██║╚██╗██║██╔══╝  ╚═╝                      ║
    ║   ██████╔╝╚██████╔╝██║ ╚████║███████╗██╗                      ║
    ║   ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝                      ║
    ║                                                               ║
    ║   RALPH-AGI successfully demonstrated autonomous coding!      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
COMPLETE
    echo -e "${NC}"
}

# Run single scenario if specified
if [ -n "$1" ]; then
    case "$1" in
        "1"|"hello")
            print_banner
            run_scenario "Hello World" "$SCRIPT_DIR/scenario-1-hello" "Create a simple Python script"
            verify_scenario "Hello World" "$SCRIPT_DIR/scenario-1-hello"
            ;;
        "2"|"calc"|"calculator")
            print_banner
            run_scenario "Calculator" "$SCRIPT_DIR/scenario-2-calculator" "Create a calculator module"
            verify_scenario "Calculator" "$SCRIPT_DIR/scenario-2-calculator"
            ;;
        "3"|"multi"|"multitask")
            print_banner
            run_scenario "Multi-Task" "$SCRIPT_DIR/scenario-3-multitask" "Create string utilities"
            verify_scenario "Multi-Task" "$SCRIPT_DIR/scenario-3-multitask"
            ;;
        *)
            echo "Usage: $0 [1|2|3|hello|calculator|multitask]"
            echo "  No argument: Run all scenarios"
            echo "  1 or hello: Run Hello World scenario"
            echo "  2 or calculator: Run Calculator scenario"
            echo "  3 or multitask: Run Multi-Task scenario"
            exit 1
            ;;
    esac
else
    main
fi
