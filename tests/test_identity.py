from ti import identity


def test_initials_and_order_link_but_twins_do_not():
    assert identity.name_sim("K.Umesh", "Komire Umesh") >= 95
    assert identity.name_sim("Umesh K", "Komire Umesh") >= 95
    assert identity.name_sim("Md.Zian", "Mohammed Zian") == 100
    assert identity.name_sim("Gurram Shashank", "Gurram Sushant") <= 70
