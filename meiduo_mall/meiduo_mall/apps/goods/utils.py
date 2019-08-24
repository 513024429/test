from orders.models import SKUComment


def get_breadcrumb(category):
    """
    面包屑导航
    :param category: 当前选择的三级类别
    """
    # 获取一级类别
    cat1 = category.parent.parent
    # 给一级类型多指定一个url
    cat1.url = cat1.goodschannel_set.all()[0].url
    breadcrumb = {
        'cat1': cat1,
        'cat2': category.parent,
        'cat3': category
    }

    return breadcrumb
def get_commnets(sku_id):
    skucomments=SKUComment.objects.filter(sku_id=sku_id)
    if len(skucomments)<1:
        return ([], 0)
    count=skucomments.count()
    comments=[]
    for skucomment in skucomments:
        username=skucomment.username
        if username=='null':
            username='匿名用户'
        else:
            username=username[0]+'****'+username[-1]
        commnet={
            'username':username,
            'desc':skucomment.comment
        }
        comments.append(commnet)
    return (comments,count)