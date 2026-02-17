"""Authorization verification module.

Ensures the operator confirms they have explicit written permission
to scan the target before any scanning begins.
"""

import sys


_AUTHORIZATION_WARNING = """
{line}
  AUTHORIZATION REQUIRED
{line}

  Target: {target}

  You are about to scan a system for vulnerabilities.
  This action is ONLY permitted if you have EXPLICIT WRITTEN
  AUTHORIZATION from the system owner.

  Unauthorized scanning is a federal crime under the CFAA
  (18 U.S. Code Section 1030) and equivalent laws worldwide.

{line}
"""


def require_authorization(target: str, skip_prompt: bool = False) -> bool:
    """Prompt the operator to confirm authorization before scanning.

    Args:
        target: The target host being scanned.
        skip_prompt: If True, skip the interactive prompt (for scripted use
                     where authorization has been pre-verified).

    Returns:
        True if authorization was confirmed, False otherwise.
    """
    line = "=" * 60

    if skip_prompt:
        print(f"\n[*] Authorization pre-confirmed for target: {target}")
        return True

    print(_AUTHORIZATION_WARNING.format(target=target, line=line))

    try:
        response = input(
            "  Do you have explicit written authorization to scan this target?\n"
            "  Type 'YES' to confirm: "
        )
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if response.strip() == "YES":
        print(f"\n[+] Authorization confirmed for: {target}")
        return True

    return False
