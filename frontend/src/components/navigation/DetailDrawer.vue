<template>
  <v-navigation-drawer
      v-model="display_detail"
      clipped
      app
      right
      mobile-breakpoint="0"
      width="400"
  >
    <v-list-item class="px-2" >
      <v-list-item-avatar color="#41b883">
        <v-icon > fas fa fa-question</v-icon>
      </v-list-item-avatar>

      <v-list-item-title>Details</v-list-item-title>

      <v-btn
          icon
          @click.stop="display_detail = !display_detail"
      >
        <v-icon>{{faIcon("right_arrow")}}</v-icon>
      </v-btn>
    </v-list-item>

    <v-divider></v-divider>
    <div v-if="display_detail">

    <info-node-detail
        v-model="display_detail"
        v-if="show_type === 'info_node'"
        :data="detail_info"
    />
    <search-help v-if="show_type === 'help'"/>
    <study-overview v-if="show_type === 'study'" :study="detail_info"/>

    </div>

  </v-navigation-drawer>
</template>

<script>


import {IconsMixin} from "../../icons";
import SearchHelp from "../search/SearchHelp";
import InfoNodeDetail from "../detail/InfoNodeDetail";
import StudyOverview from "../detail/StudyOverview";

export default {
  name: 'DetailDrawer',
  components: {SearchHelp, StudyOverview,InfoNodeDetail},
  mixins: [IconsMixin],
  data: () => ({
    drawer: false,
  }),
  computed:{
    display_detail:  {
      get() {
        return this.$store.state.display_detail
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "display_detail",
          value: value,
        })
      }
    },
    detail_info: {
      get() {
        return this.$store.state.detail_info
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "detail_info",
          value: value,
        })
      }
    },
    show_type: {
      get() {
        return this.$store.state.show_type
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "show_type",
          value: value,
        })
      }
    }
  }
}
</script>

<style scoped>
</style>