"""Command registration for the Eagle Eval CLI."""

from eagle_eval.commands.assistants import install_assistants
from eagle_eval.commands.context import context_group
from eagle_eval.commands.doctor import doctor
from eagle_eval.commands.pipeline import gate, generate, upload
from eagle_eval.commands.runs import compare, run
from eagle_eval.commands.scorer import scorer_group
from eagle_eval.commands.services import services
from eagle_eval.commands.setup import init_command
from eagle_eval.commands.status import status
from eagle_eval.commands.target_compare import compare_targets
from eagle_eval.commands.updates import update


def register_commands(cli):
    for command in (
        init_command,
        generate,
        gate,
        upload,
        run,
        compare,
        compare_targets,
        status,
        doctor,
        services,
        context_group,
        scorer_group,
        install_assistants,
        update,
    ):
        cli.add_command(command)
