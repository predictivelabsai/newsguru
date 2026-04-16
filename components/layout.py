from fasthtml.common import *
from monsterui.all import *


def NavBar_(sess=None):
    user_name = None
    if sess and isinstance(sess, dict):
        user_name = sess.get("user_name")

    auth_section = (
        DivLAligned(
            Span(user_name, cls="text-sm"),
            A("Logout", href="/auth/logout", cls="uk-button uk-button-text uk-button-small"),
            cls="gap-2",
        ) if user_name else
        DivLAligned(
            A("Login", href="/login", cls="uk-button uk-button-default uk-button-small"),
            A("Register", href="/register", cls="uk-button uk-button-primary uk-button-small"),
            cls="gap-2",
        )
    )

    return Div(
        DivFullySpaced(
            A(
                DivLAligned(
                    UkIcon("newspaper", height=24),
                    Span("NewsGuru", cls="text-xl font-bold"),
                    cls="gap-2",
                ),
                href="/",
                cls="no-underline",
            ),
            DivLAligned(
                A("Home", href="/", cls="uk-button uk-button-text uk-button-small"),
                auth_section,
                cls="gap-3",
            ),
        ),
        cls="uk-container uk-container-expand p-4 border-b mb-4",
    )


def page_shell(*content, title="NewsGuru"):
    return Title(title), NavBar_(), Container(*content)
