def load_all_models():
    import model.user                                    # noqa: F401
    import model.profiles.buyer                          # noqa: F401
    import model.profiles.builder                        # noqa: F401
    import model.profiles.community                      # noqa: F401
    import model.profiles.community_admin_profile        # noqa: F401
    import model.profiles.sales_rep                      # noqa: F401
    import model.profiles.lot                            # noqa: F401
    import model.property.property                       # noqa: F401
    import model.followers                               # noqa: F401
    import model.media                                   # noqa: F401
    import model.collection                              # noqa: F401
    from src.collection.status_management.history import StatusHistory  # noqa: F401