"""Smoke-test a live Judge0: run a tiny program in every enabled language."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.coding import judge0
from apps.coding.models import Language

PROGRAMS = {
    "python": "print(sum(map(int, input().split())))",
    "c": '#include <stdio.h>\nint main(){int a,b;scanf("%d %d",&a,&b);printf("%d\\n",a+b);return 0;}',
    "cpp": "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<std::endl;}",
    "java": (
        "import java.util.*;\npublic class Main{public static void main(String[] x){"
        "Scanner s=new Scanner(System.in);System.out.println(s.nextInt()+s.nextInt());}}"
    ),
    "javascript": (
        "const [a,b]=require('fs').readFileSync(0,'utf8').trim().split(/\\s+/).map(Number);"
        "console.log(a+b);"
    ),
}


class Command(BaseCommand):
    help = "Run 'add two numbers' in each enabled language on the configured Judge0."

    def handle(self, *args, **options):
        client = judge0.get_client()
        try:
            about = client.languages()
        except judge0.Judge0Error as exc:
            raise CommandError(f"{exc}\nIs Judge0 running at {settings.JUDGE0_URL}?") from exc
        self.stdout.write(f"Judge0 reachable at {settings.JUDGE0_URL} ({len(about)} languages)")

        languages = [
            lang for lang in Language.objects.filter(is_enabled=True) if lang.slug in PROGRAMS
        ]
        if not languages:
            raise CommandError("No enabled languages. Run `manage.py seed_languages` first.")
        results = client.execute(
            [
                judge0.ExecRequest(
                    source_code=PROGRAMS[lang.slug], language_id=lang.judge0_id, stdin="20 22"
                )
                for lang in languages
            ]
        )
        failures = 0
        for lang, result in zip(languages, results, strict=True):
            ok = result.status_id == judge0.STATUS_ACCEPTED and result.stdout.strip() == "42"
            failures += not ok
            detail = (
                result.stdout.strip() or result.compile_output or result.stderr or result.status
            )
            self.stdout.write(f"{'ok ' if ok else 'FAIL'} {lang}: {detail[:200]}")
        if failures:
            raise CommandError(f"{failures} languages failed")
        self.stdout.write(self.style.SUCCESS("All languages work."))
