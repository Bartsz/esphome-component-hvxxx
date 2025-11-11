#include "esphome/core/log.h"
#include "offset_number.h"

namespace esphome
{
  namespace hvxxx
  {

    static const char *const TAG = "hvxxx.offset_number";

    void HVxxxOffsetNumber::setup()
    {
      if (this->f_.has_value())
        return;

      float value;
      if (!this->restore_value_)
      {
        value = this->initial_value_;
      }
      else
      {
        this->pref_ = global_preferences->make_preference<float>(this->get_preference_hash());
        if (!this->pref_.load(&value))
        {
          if (!std::isnan(this->initial_value_))
          {
            value = this->initial_value_;
          }
          else
          {
            value = this->traits.get_min_value();
          }
        }
      }
      this->publish_state(value);
    }

    void HVxxxOffsetNumber::update()
    {
      if (!this->f_.has_value())
        return;

      auto val = (*this->f_)();
      if (!val.has_value())
        return;

      this->publish_state(*val);
    }

    void HVxxxOffsetNumber::control(float value)
    {
      this->set_trigger_->trigger(value);

      if (this->optimistic_)
        this->publish_state(value);

      if (this->restore_value_)
        this->pref_.save(&value);
    }
    void HVxxxOffsetNumber::dump_config()
    {
      LOG_NUMBER("", "Offset Number", this);
      ESP_LOGCONFIG(TAG, "  Optimistic: %s", YESNO(this->optimistic_));
      LOG_UPDATE_INTERVAL(this);
    }

  }
}