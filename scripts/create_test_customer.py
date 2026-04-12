"""End-to-end test script: create customer, issue API key, test auth."""

import asyncio
import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Create customer
        print("1. Creating test customer...")
        resp = await client.post(
            "/v1/customers",
            json={
                "name": "Alex Testperson",
                "email": "alex@testcompany.com",
                "company_name": "Test Company Inc.",
            },
        )
        if resp.status_code == 409:
            print("   Customer already exists, fetching by creating with unique email...")
            resp = await client.post(
                "/v1/customers",
                json={
                    "name": "Alex Testperson",
                    "email": f"alex+{id(client)}@testcompany.com",
                    "company_name": "Test Company Inc.",
                },
            )
        if resp.status_code != 201:
            print(f"   FAILED: {resp.status_code} {resp.text}")
            sys.exit(1)
        customer = resp.json()
        print(f"   Customer created: {customer['id']}")

        # 2. Issue API key
        print("2. Creating API key...")
        resp = await client.post(
            f"/v1/customers/{customer['id']}/api-keys",
            json={"name": "Test Script Key"},
        )
        if resp.status_code != 201:
            print(f"   FAILED: {resp.status_code} {resp.text}")
            sys.exit(1)
        key_data = resp.json()
        api_key = key_data["key"]
        print(f"   API key: {api_key}")
        print(f"   Prefix:  {key_data['key_prefix']}")
        print(f"   WARNING: {key_data['warning']}")

        # 3. Test public health
        print("3. Testing public health endpoint...")
        resp = await client.get("/health")
        assert resp.status_code == 200
        print(f"   /health: {resp.json()['status']}")

        # 4. Test authenticated health
        print("4. Testing authenticated health endpoint...")
        resp = await client.get(
            "/v1/health",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if resp.status_code != 200:
            print(f"   FAILED: {resp.status_code} {resp.text}")
            sys.exit(1)
        health = resp.json()
        print(f"   /v1/health: {health['status']} (customer: {health['customer_id']})")

        # 5. Verify unauthenticated request is blocked
        print("5. Verifying unauthenticated request is blocked...")
        resp = await client.get("/v1/health")
        assert resp.status_code == 401
        print(f"   /v1/health (no key): 401 as expected")

    print("\nAll checks passed. Phase 1 foundation is working.")


if __name__ == "__main__":
    asyncio.run(main())
