from arclet.entari.config import BasicConfModel, model_field


class SignConfig(BasicConfModel):
    max: int = model_field(default=200, description="信赖最大值")
