#!/bin/bash

# API Endpoint Testing Script for Org Archivist Backend
# Tests CORS functionality and basic API endpoints
# Usage: ./test-api-endpoints.sh [BASE_URL]
# Example: ./test-api-endpoints.sh http://localhost:8001

set -e

BASE_URL="${1:-http://localhost:8001}"
TEST_EMAIL="testuser-$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
NC="\033[0m" # No Color

echo -e "${BOLD}========================================${NC}"
echo -e "${BOLD}  Org Archivist API Endpoint Tests${NC}"
echo -e "${BOLD}========================================${NC}"
echo ""
echo "Testing against: $BASE_URL"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check Endpoint${NC}"
echo "GET $BASE_URL/api/health"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Status: $HTTP_CODE"
    echo "Response: $BODY"
else
    echo -e "${RED}✗ FAILED${NC} - Expected 200, got $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 2: CORS Preflight
echo -e "${YELLOW}Test 2: CORS Preflight Request${NC}"
echo "OPTIONS $BASE_URL/api/documents"
echo "Origin: http://localhost:3000"
RESPONSE=$(curl -s -i -X OPTIONS "$BASE_URL/api/documents" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: authorization")

if echo "$RESPONSE" | grep -q "access-control-allow-origin: http://localhost:3000"; then
    echo -e "${GREEN}✓ PASSED${NC} - CORS headers present"
    echo "$RESPONSE" | grep "access-control"
else
    echo -e "${RED}✗ FAILED${NC} - CORS headers missing or incorrect"
    echo "$RESPONSE"
    exit 1
fi
echo ""

# Test 3: Document List (No Auth)
echo -e "${YELLOW}Test 3: Document List Endpoint (No Auth)${NC}"
echo "GET $BASE_URL/api/documents"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/documents")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Status: $HTTP_CODE"
    echo "Response: $BODY"
else
    echo -e "${RED}✗ FAILED${NC} - Expected 200, got $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 4: Register New User
echo -e "${YELLOW}Test 4: User Registration${NC}"
echo "POST $BASE_URL/api/auth/register"
echo "Email: $TEST_EMAIL"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$TEST_PASSWORD\",
        \"full_name\": \"Test User\",
        \"role\": \"writer\"
    }")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Status: $HTTP_CODE"
    echo "Response: $BODY"
    USER_ID=$(echo "$BODY" | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
    echo "User ID: $USER_ID"
else
    echo -e "${RED}✗ FAILED${NC} - Expected 201, got $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 5: Login
echo -e "${YELLOW}Test 5: User Login${NC}"
echo "POST $BASE_URL/api/auth/login"
echo "Email: $TEST_EMAIL"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$TEST_PASSWORD\"
    }")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Status: $HTTP_CODE"
    ACCESS_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo "Access token obtained: ${ACCESS_TOKEN:0:50}..."
else
    echo -e "${RED}✗ FAILED${NC} - Expected 200, got $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 6: Authenticated Endpoint
echo -e "${YELLOW}Test 6: Authenticated Endpoint${NC}"
echo "GET $BASE_URL/api/auth/me"
echo "Authorization: Bearer [token]"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/auth/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Status: $HTTP_CODE"
    echo "Response: $BODY"
else
    echo -e "${RED}✗ FAILED${NC} - Expected 200, got $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Test 7: Authenticated Document List
echo -e "${YELLOW}Test 7: Authenticated Document List${NC}"
echo "GET $BASE_URL/api/documents"
echo "Authorization: Bearer [token]"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/documents" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC} - Status: $HTTP_CODE"
    echo "Response: $BODY"
else
    echo -e "${RED}✗ FAILED${NC} - Expected 200, got $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi
echo ""

# Summary
echo -e "${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}All Tests Passed!${NC}"
echo -e "${BOLD}========================================${NC}"
echo ""
echo "Summary:"
echo "  - Health check: ✓"
echo "  - CORS preflight: ✓"
echo "  - Document list (no auth): ✓"
echo "  - User registration: ✓"
echo "  - User login: ✓"
echo "  - Authenticated endpoint: ✓"
echo "  - Authenticated document list: ✓"
echo ""
