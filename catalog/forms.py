from django import forms

from .models import ProductReview


class ProductReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        label='Оценка',
        coerce=int,
        choices=[(i, str(i)) for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'star-rating__input'}),
        error_messages={'required': 'Выберите оценку от 1 до 5'},
    )
    comment = forms.CharField(
        label='Комментарий',
        widget=forms.Textarea(
            attrs={
                'rows': 4,
                'placeholder': 'Расскажите о товаре: качество, запах, расход…',
                'maxlength': 2000,
            }
        ),
        max_length=2000,
        error_messages={'required': 'Напишите короткий комментарий'},
    )

    class Meta:
        model = ProductReview
        fields = ('rating', 'comment')
