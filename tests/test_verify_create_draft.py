import asyncio
import os
import sys

# Add project root to path
sys.path.append("e:/code/workspace/1230/rednote-research-agent")

from rednote_research.services.publisher import PublishService

async def verify_create_draft():
    print("Verifying create_draft...")
    service = PublishService(output_base_dir="e:/code/workspace/1230/rednote-research-agent/output/test_verify")
    
    topic = "Test Topic"
    summary = "Test Summary"
    key_findings = ["Finding 1", "Finding 2"]
    sections = [{"title": "Section 1", "content": "Content 1"}]
    notes = []
    
    try:
        draft = service.create_draft(
            topic=topic,
            summary=summary,
            key_findings=key_findings,
            sections=sections,
            notes=notes
        )
        print(f"Draft created successfully: {draft.id}")
        print(f"Draft title: {draft.title}")
        return True
    except Exception as e:
        print(f"Create draft failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_create_draft())
    if success:
        print("VERIFICATION SUCCESS")
        exit(0)
    else:
        print("VERIFICATION FAILED")
        exit(1)
