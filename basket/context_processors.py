from .basket import Basket


def basket(request):
    """Make `basket` available in all templates (header count, summary, etc.)."""
    return {"basket": Basket(request)}
